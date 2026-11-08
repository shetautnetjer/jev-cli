//! Local projector/replay CLI. Discovery remains with the existing Skills MCP.
use serde::de::{self, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer};
use serde_json::{json, Value};
use std::collections::HashSet;
use std::fmt;
use skills_rs::{project, replay, verify, Projection};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

const USAGE: &str = "skills-rs project <skill-dir> [--out <projection.json>] | verify <projection.json> <skill-dir> | replay <projection.json> <contract.json> <state.json> <receipt.json> [--skill-dir <directory>]";

struct UniqueKeys;

impl<'de> Deserialize<'de> for UniqueKeys {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct Check;
        impl<'de> Visitor<'de> for Check {
            type Value = ();
            fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
                formatter.write_str("JSON without duplicate object keys")
            }
            fn visit_map<M: MapAccess<'de>>(self, mut map: M) -> Result<(), M::Error> {
                let mut keys = HashSet::new();
                while let Some(key) = map.next_key::<String>()? {
                    if !keys.insert(key) {
                        return Err(de::Error::custom("duplicate object key"));
                    }
                    map.next_value::<UniqueKeys>()?;
                }
                Ok(())
            }
            fn visit_seq<S: SeqAccess<'de>>(self, mut seq: S) -> Result<(), S::Error> {
                while seq.next_element::<UniqueKeys>()?.is_some() {}
                Ok(())
            }
            fn visit_bool<E: de::Error>(self, _: bool) -> Result<(), E> { Ok(()) }
            fn visit_i64<E: de::Error>(self, _: i64) -> Result<(), E> { Ok(()) }
            fn visit_u64<E: de::Error>(self, _: u64) -> Result<(), E> { Ok(()) }
            fn visit_f64<E: de::Error>(self, _: f64) -> Result<(), E> { Ok(()) }
            fn visit_str<E: de::Error>(self, _: &str) -> Result<(), E> { Ok(()) }
            fn visit_string<E: de::Error>(self, _: String) -> Result<(), E> { Ok(()) }
            fn visit_unit<E: de::Error>(self) -> Result<(), E> { Ok(()) }
        }
        deserializer.deserialize_any(Check).map(|()| Self)
    }
}

fn read_json(path: &str) -> Result<Value, String> {
    let bytes = fs::read(path).map_err(|_| "Cannot read input file".to_string())?;
    serde_json::from_slice::<UniqueKeys>(&bytes)
        .map_err(|_| "Input is invalid JSON or contains duplicate object keys".to_string())?;
    serde_json::from_slice(&bytes).map_err(|_| "Input is not valid JSON".to_string())
}

fn read_projection(path: &str) -> Result<Projection, String> {
    serde_json::from_value(read_json(path)?)
        .map_err(|_| "Input is not a supported skill projection".to_string())
}

fn publish_new(path: &Path, bytes: &[u8]) -> Result<(), String> {
    let parent = path.parent().filter(|p| !p.as_os_str().is_empty()).unwrap_or(Path::new("."));
    let nonce = SystemTime::now().duration_since(UNIX_EPOCH)
        .map_err(|_| "Cannot create output timestamp".to_string())?.as_nanos();
    let temporary = parent.join(format!(".skills-rs-{}-{nonce}.tmp", std::process::id()));
    let mut file = OpenOptions::new().write(true).create_new(true).open(&temporary)
        .map_err(|_| "Cannot create projection output".to_string())?;
    let outcome = (|| {
        file.write_all(bytes).map_err(|_| "Cannot write projection output".to_string())?;
        file.sync_all().map_err(|_| "Cannot flush projection output".to_string())?;
        // Publishing with a hard link refuses an existing destination atomically.
        fs::hard_link(&temporary, path)
            .map_err(|_| "Cannot publish projection; destination must not exist".to_string())
    })();
    drop(file);
    let _ = fs::remove_file(&temporary);
    outcome
}

fn run(args: &[String]) -> Result<Value, String> {
    match args.first().map(String::as_str) {
        Some("project") if args.len() == 2 || (args.len() == 4 && args[2] == "--out") => {
            let projection = project(Path::new(&args[1]))?;
            let value = serde_json::to_value(&projection).map_err(|_| "Cannot encode projection")?;
            if args.len() == 4 {
                let mut bytes = serde_json::to_vec_pretty(&value).map_err(|_| "Cannot encode projection")?;
                bytes.push(b'\n');
                publish_new(Path::new(&args[3]), &bytes)?;
            }
            Ok(value)
        }
        Some("verify") if args.len() == 3 => {
            let projection = read_projection(&args[1])?;
            verify(&projection, Path::new(&args[2]))?;
            Ok(json!({"status":"verified", "artifact_sha256":projection.artifact_sha256,
                      "source_verified":true, "authority_granted":false}))
        }
        Some("replay") if args.len() == 5 || (args.len() == 7 && args[5] == "--skill-dir") => {
            let projection = read_projection(&args[1])?;
            if args.len() == 7 {
                verify(&projection, Path::new(&args[6]))?;
            }
            let mut output = replay(
                &projection, &read_json(&args[2])?, &read_json(&args[3])?, &read_json(&args[4])?,
            )?;
            output["source_verified"] = Value::Bool(args.len() == 7);
            Ok(output)
        }
        _ => Err(USAGE.to_string()),
    }
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.first().is_some_and(|arg| arg == "--help" || arg == "-h") {
        println!("{USAGE}");
        return;
    }
    match run(&args) {
        Ok(value) => println!("{value}"),
        Err(error) => {
            println!("{}", json!({"status":"error", "error":error,
                                "inference_attempted":false, "authority_granted":false}));
            std::process::exit(2);
        }
    }
}
