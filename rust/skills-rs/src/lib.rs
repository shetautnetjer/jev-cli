//! Compile a qualified declarative method and replay retained receipts, without inference.

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::Path;
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};

const ADAPTER_SHA256: &str = "ca0db22383593fb3592abb289749bb657d877a44f1141d0cd6de78750030b712";
const SCHEMA: &str = "jev-cli/skill-projection-v1";
const SOURCE_FILES: [&str; 3] = ["SKILL.md", "decision.mthds", "jev_method.py"];
type Object = Map<String, Value>;
type Checked<T> = Result<T, String>;

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Projection {
    pub schema_version: String,
    pub projector_version: String,
    pub source_files: BTreeMap<String, String>,
    pub domain: String,
    pub entrypoint: String,
    pub branches: BTreeMap<String, String>,
    pub default_handler: String,
    pub artifact_sha256: String,
}

fn require(ok: bool, message: &str) -> Checked<()> {
    if ok { Ok(()) } else { Err(message.into()) }
}

fn object(value: &Value) -> Checked<&Object> {
    value.as_object().ok_or_else(|| "Expected a JSON object".into())
}

fn field<'a>(obj: &'a Object, key: &str) -> Checked<&'a Value> {
    obj.get(key).ok_or_else(|| "Missing required field or graph reference".into())
}

fn string<'a>(obj: &'a Object, key: &str) -> Checked<&'a str> {
    field(obj, key)?.as_str().ok_or_else(|| "Expected string field".into())
}

fn allowed(obj: &Object, names: &[&str]) -> Checked<()> {
    require(obj.keys().all(|k| names.contains(&k.as_str())), "Unsupported field")
}

fn equal_keys(obj: &Object, names: &[&str]) -> Checked<()> {
    require(obj.len() == names.len() && names.iter().all(|k| obj.contains_key(*k)), "Unexpected field set")
}

fn digest(bytes: &[u8]) -> String { format!("{:x}", Sha256::digest(bytes)) }

/// Match Python json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(",", ":")).
/// JSON integers must fit i64/u64; floats use finite IEEE-754 binary64 semantics.
/// Arbitrary-precision parsing preserves integer spelling so oversized values can be rejected.
fn canonical(value: &Value) -> Checked<String> {
    match value {
        Value::Null => Ok("null".into()),
        Value::Bool(b) => Ok(b.to_string()),
        Value::String(s) => serde_json::to_string(s).map_err(|_| "Invalid JSON string".into()),
        Value::Number(n) => {
            let raw = n.to_string();
            if !raw.contains(['.', 'e', 'E']) {
                return n.as_i64().map(|v| v.to_string()).or_else(|| n.as_u64().map(|v| v.to_string()))
                    .ok_or_else(|| "Integer outside supported i64/u64 range".into());
            }
            let f = n.as_f64().filter(|v| v.is_finite()).ok_or("Non-finite JSON number")?;
            Ok(python_float(f))
        }
        Value::Array(items) => Ok(format!("[{}]", items.iter().map(canonical).collect::<Checked<Vec<_>>>()?.join(","))),
        Value::Object(obj) => {
            let mut keys: Vec<_> = obj.keys().collect();
            keys.sort();
            let parts = keys.into_iter().map(|k| {
                Ok(format!("{}:{}", serde_json::to_string(k).map_err(|_| "Invalid key")?, canonical(&obj[k])?))
            }).collect::<Checked<Vec<_>>>()?;
            Ok(format!("{{{}}}", parts.join(",")))
        }
    }
}

fn python_float(value: f64) -> String {
    if value == 0.0 { return if value.is_sign_negative() { "-0.0" } else { "0.0" }.into(); }
    let sign = if value.is_sign_negative() { "-" } else { "" };
    let raw = format!("{:?}", value.abs());
    let (mantissa, exponent) = match raw.split_once('e') {
        Some((m, e)) => (m, e.parse::<i32>().expect("Rust float exponent")),
        None => (raw.as_str(), 0),
    };
    let dot = mantissa.find('.').unwrap_or(mantissa.len()) as i32;
    let digits: String = mantissa.chars().filter(|c| *c != '.').collect();
    let leading = digits.bytes().take_while(|c| *c == b'0').count();
    let digits = digits[leading..].trim_end_matches('0');
    let exponent = exponent + dot - leading as i32 - 1;
    if !(-4..16).contains(&exponent) {
        let fraction = if digits.len() > 1 { format!(".{}", &digits[1..]) } else { String::new() };
        format!("{sign}{}{fraction}e{}{:02}", &digits[..1], if exponent < 0 { '-' } else { '+' }, exponent.abs())
    } else {
        let pos = exponent + 1;
        if pos <= 0 {
            format!("{sign}0.{}{}", "0".repeat((-pos) as usize), digits)
        } else if pos as usize >= digits.len() {
            format!("{sign}{digits}{}.0", "0".repeat(pos as usize - digits.len()))
        } else {
            format!("{sign}{}.{}", &digits[..pos as usize], &digits[pos as usize..])
        }
    }
}

fn hash_json(value: &Value) -> Checked<String> { Ok(digest(canonical(value)?.as_bytes())) }

fn projection_hash(projection: &Projection) -> Checked<String> {
    let mut value = serde_json::to_value(projection).map_err(|_| "Cannot serialize projection")?;
    value.as_object_mut().ok_or("Invalid projection")?.remove("artifact_sha256");
    hash_json(&value)
}

fn valid_hash(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
}

// Qualified local subset of Pipelex's snake_case code and dotted domain validators.
// Cross-package domains and imported pipe references need separate qualification.
fn valid_pipe_code(value: &str) -> bool {
    value.as_bytes().first().is_some_and(u8::is_ascii_lowercase)
        && value.bytes().all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
}

fn valid_domain(value: &str) -> bool {
    value.split('.').all(valid_pipe_code)
}

fn validate_projection(projection: &Projection) -> Checked<()> {
    require(projection.schema_version == SCHEMA && projection.projector_version == env!("CARGO_PKG_VERSION"), "Unsupported projection version")?;
    require(projection.source_files.len() == SOURCE_FILES.len() && SOURCE_FILES.iter().all(|k| projection.source_files.get(*k).is_some_and(|v| valid_hash(v))), "Invalid projection source hashes")?;
    require(projection.source_files.get("jev_method.py").map(String::as_str) == Some(ADAPTER_SHA256), "Unqualified adapter source")?;
    require(valid_domain(&projection.domain) && valid_pipe_code(&projection.entrypoint), "Invalid projection names")?;
    require(projection.branches == BTreeMap::from([
        ("ready".into(), "jev_return_decision".into()),
        ("needs_evidence".into(), "jev_needs_evidence".into()),
    ]) && projection.default_handler == "jev_unknown_route", "Unsupported projection handler mapping")?;
    require(projection.artifact_sha256 == projection_hash(projection)?, "Projection integrity mismatch")
}

fn typed_node(node: &Object, kind: &str, inputs: Value, extra: &[&str]) -> Checked<()> {
    let mut fields = vec!["type", "description", "inputs", "output"];
    fields.extend_from_slice(extra);
    allowed(node, &fields)?;
    require(string(node, "type")? == kind && field(node, "inputs")? == &inputs && string(node, "output")? == "DecisionOutput", "Unsupported node type or slot wiring")?;
    string(node, "description")?;
    Ok(())
}

/// Compile the qualified function/condition subset. Python is hashed, never executed.
pub fn project(skill_dir: &Path) -> Checked<Projection> {
    let mut source_files = BTreeMap::new();
    let mut method = Vec::new();
    for name in SOURCE_FILES {
        let bytes = fs::read(skill_dir.join(name)).map_err(|_| format!("Cannot read required source: {name}"))?;
        require(!bytes.is_empty(), "Empty skill source")?;
        if name == "decision.mthds" { method = bytes.clone(); }
        source_files.insert(name.into(), digest(&bytes));
    }
    require(source_files["jev_method.py"] == ADAPTER_SHA256, "Unqualified adapter source")?;
    let text = std::str::from_utf8(&method).map_err(|_| "Method is not UTF-8")?;
    let toml: toml::Value = toml::from_str(text).map_err(|_| "Invalid method TOML")?;
    let value = serde_json::to_value(toml).map_err(|_| "Method contains unsupported values")?;
    let root = object(&value)?;
    allowed(root, &["domain", "description", "main_pipe", "concept", "pipe"])?;
    let domain = string(root, "domain")?;
    require(valid_domain(domain), "Unsupported method domain syntax")?;
    if let Some(description) = root.get("description") { require(description.is_string(), "Invalid method description")?; }
    let entrypoint = string(root, "main_pipe")?;
    require(valid_pipe_code(entrypoint), "Unsupported main pipe syntax")?;
    let concepts = object(field(root, "concept")?)?;
    equal_keys(concepts, &["DecisionInput", "DecisionOutput"])?;
    for name in ["DecisionInput", "DecisionOutput"] {
        let c = object(field(concepts, name)?)?;
        allowed(c, &["description", "structure"])?;
        require(string(c, "structure")? == name && string(c, "description").is_ok(), "Unsupported concept structure")?;
    }
    let pipes = object(field(root, "pipe")?)?;
    require(pipes.keys().all(|k| valid_pipe_code(k)), "Unsupported pipe code syntax")?;
    let sequence = object(field(pipes, entrypoint)?)?;
    typed_node(sequence, "PipeSequence", json!({"packet":"DecisionInput"}), &["steps"])?;
    let steps = field(sequence, "steps")?.as_array().ok_or("Invalid sequence steps")?;
    require(steps.len() == 2, "Only the qualified two-step sequence is supported")?;
    let mut names = vec![entrypoint];
    for (step, expected_result) in steps.iter().zip(["decision", "result"]) {
        let s = object(step)?;
        equal_keys(s, &["pipe", "result"])?;
        require(string(s, "result")? == expected_result, "Unsupported sequence result wiring")?;
        names.push(string(s, "pipe")?);
    }
    let evaluate = object(field(pipes, names[1])?)?;
    typed_node(evaluate, "PipeFunc", json!({"packet":"DecisionInput"}), &["function_name"])?;
    require(string(evaluate, "function_name")? == "jev_evaluate_contract", "Unsupported evaluation function")?;
    let route = object(field(pipes, names[2])?)?;
    typed_node(route, "PipeCondition", json!({"decision":"DecisionOutput"}), &["expression", "outcomes", "default_outcome"])?;
    require(string(route, "expression")? == "decision.disposition", "Unsupported condition expression")?;
    let outcomes = object(field(route, "outcomes")?)?;
    equal_keys(outcomes, &["ready", "needs_evidence"])?;
    let mut branches = BTreeMap::new();
    for (disposition, handler) in [("ready", "jev_return_decision"), ("needs_evidence", "jev_needs_evidence")] {
        let name = string(outcomes, disposition)?;
        let node = object(field(pipes, name)?)?;
        typed_node(node, "PipeFunc", json!({"decision":"DecisionOutput"}), &["function_name"])?;
        require(string(node, "function_name")? == handler, "Unsupported branch function")?;
        names.push(name);
        branches.insert(disposition.into(), handler.into());
    }
    let default = string(route, "default_outcome")?;
    names.push(default);
    let node = object(field(pipes, default)?)?;
    typed_node(node, "PipeFunc", json!({"decision":"DecisionOutput"}), &["function_name"])?;
    require(string(node, "function_name")? == "jev_unknown_route", "Unsupported default function")?;
    let distinct: BTreeSet<_> = names.iter().copied().collect();
    require(distinct.len() == 6 && pipes.len() == 6 && pipes.keys().all(|k| distinct.contains(k.as_str())), "Unexpected, unreachable, or cyclic method nodes")?;
    let mut projection = Projection {
        schema_version: SCHEMA.into(), projector_version: env!("CARGO_PKG_VERSION").into(),
        source_files, domain: domain.into(), entrypoint: entrypoint.into(), branches,
        default_handler: "jev_unknown_route".into(), artifact_sha256: String::new(),
    };
    projection.artifact_sha256 = projection_hash(&projection)?;
    Ok(projection)
}

/// Reopen and recompile all source files, then compare the full artifact.
pub fn verify(projection: &Projection, skill_dir: &Path) -> Checked<()> {
    validate_projection(projection)?;
    require(projection == &project(skill_dir)?, "Projection differs from current sources")
}

fn normalize_contract(value: &Value) -> Checked<Value> {
    let c = object(value)?;
    allowed(c, &["id", "version", "model", "questions", "composition", "tags"])?;
    let id = string(c, "id")?;
    require(!id.is_empty() && id.len() <= 128 && id.as_bytes()[0].is_ascii_alphanumeric() && id.bytes().all(|b| b.is_ascii_alphanumeric() || b"_.-".contains(&b)), "Invalid contract id")?;
    string(c, "version")?;
    if c.contains_key("model") { string(c, "model")?; }
    let questions = object(field(c, "questions")?)?;
    let mut normalized_questions = Object::new();
    for (id, raw) in questions {
        let q = object(raw)?;
        allowed(q, &["type", "instructions", "criteria"])?;
        let kind = string(q, "type")?;
        let instructions = field(q, "instructions")?;
        require(instructions.is_string() || instructions.is_array() || instructions.is_object(), "Invalid question instructions")?;
        let mut normalized = q.clone();
        match kind {
            "choice" => { let criteria = object(field(q, "criteria")?)?; require((2..=255).contains(&criteria.len()), "Invalid choice option count")?; }
            "score" => { let criteria = field(q, "criteria")?.as_array().ok_or("Invalid score criteria")?; require((2..=10).contains(&criteria.len()), "Invalid score level count")?; }
            "noul" => {
                if let Some(criteria) = q.get("criteria").filter(|v| !v.is_null()) {
                    let criteria = object(criteria)?;
                    allowed(criteria, &["true", "false"])?;
                    normalized.insert("criteria".into(), Value::Object(criteria.iter().filter(|(_,v)| !v.is_null()).map(|(k,v)| (k.clone(),v.clone())).collect()));
                } else { normalized.remove("criteria"); }
            }
            _ => return Err("Unsupported question type".into()),
        }
        normalized_questions.insert(id.clone(), Value::Object(normalized));
    }
    let mut normalized = c.clone();
    normalized.insert("questions".into(), Value::Object(normalized_questions));
    normalized.entry("model").or_insert(json!("jev-latest"));
    normalized.entry("tags").or_insert(json!([]));
    require(normalized["tags"].as_array().is_some_and(|a| a.iter().all(Value::is_string)), "Invalid contract tags")?;
    if let Some(policy) = c.get("composition").filter(|v| !v.is_null()) {
        let policy = object(policy)?;
        allowed(policy, &["rules", "default"])?;
        require(field(policy, "default")?.is_string(), "Method requires string routing composition")?;
        let mut policy = policy.clone();
        policy.entry("rules").or_insert(json!([]));
        for rule in policy["rules"].as_array().ok_or("Invalid composition rules")? {
            let rule = object(rule)?;
            equal_keys(rule, &["question", "operator", "value", "result"])?;
            require(questions.contains_key(string(rule, "question")?), "Unknown composition question")?;
            require(["eq", "gte", "lte"].contains(&string(rule, "operator")?), "Unsupported composition operator")?;
            let operand = field(rule, "value")?;
            require(operand.is_string() || operand.is_boolean() || operand.is_number(), "Invalid composition operand")?;
            require(field(rule, "result")?.is_string(), "Method requires string routing composition")?;
        }
        normalized.insert("composition".into(), Value::Object(policy));
    } else {
        normalized.remove("composition");
        require(questions.len() == 1 && questions.values().next().and_then(|q| q.get("type")).and_then(Value::as_str) == Some("choice"), "Method requires string routing composition")?;
    }
    let normalized = Value::Object(normalized);
    canonical(&normalized)?;
    Ok(normalized)
}

fn finite(value: &Value) -> Checked<f64> {
    value.as_f64().filter(|v| v.is_finite()).ok_or_else(|| "Expected a finite number".into())
}

fn probability(value: &Value) -> Checked<f64> {
    let number = finite(value)?;
    require((0.0..=1.0).contains(&number), "Probability outside [0,1]")?;
    Ok(number)
}

fn validate_answers(answers: &Object, questions: &Object) -> Checked<()> {
    require(answers.len() == questions.len() && answers.keys().all(|k| questions.contains_key(k)), "Answer IDs do not match contract")?;
    for (id, q) in questions {
        let q = object(q)?;
        let a = object(&answers[id])?;
        allowed(a, &["id", "type", "value", "probabilities", "confidence"])?;
        let kind = string(q, "type")?;
        require(string(a, "id")? == id && string(a, "type")? == kind, "Answer identity/type mismatch")?;
        let value = field(a, "value")?;
        if kind == "noul" {
            probability(value)?;
            require(a.get("probabilities").is_none_or(Value::is_null) && a.get("confidence").is_none_or(Value::is_null), "Noul receipt must not carry a distribution or confidence")?;
            continue;
        }
        let expected: BTreeSet<String> = if kind == "choice" {
            object(field(q, "criteria")?)?.keys().cloned().collect()
        } else {
            (0..field(q, "criteria")?.as_array().ok_or("Invalid score criteria")?.len()).map(|i| i.to_string()).collect()
        };
        let distribution = object(field(a, "probabilities")?)?;
        require(distribution.keys().cloned().collect::<BTreeSet<_>>() == expected, "Answer distribution labels mismatch")?;
        let probabilities = distribution.iter().map(|(k,v)| Ok((k.as_str(), probability(v)?))).collect::<Checked<Vec<_>>>()?;
        let total: f64 = probabilities.iter().map(|(_,v)| v).sum();
        require((total - 1.0).abs() <= 0.01, "Answer distribution is not normalized")?;
        probability(field(a, "confidence")?)?;
        if kind == "choice" {
            let choice = value.as_str().ok_or("Choice answer must be a string")?;
            require(expected.contains(choice), "Choice answer outside contract options")?;
            let chosen = probability(&distribution[choice])?;
            require(probabilities.iter().all(|(_,p)| chosen >= p - 1e-6), "Choice answer is not a maximum probability option")?;
        } else {
            let score = finite(value)?;
            require((0.0..=(expected.len() - 1) as f64).contains(&score), "Score outside contract scale")?;
            let weighted: f64 = probabilities.iter().map(|(k,p)| k.parse::<usize>().expect("validated score index") as f64 * p).sum();
            require((score - weighted).abs() <= 0.02, "Score does not match distribution expectation")?;
        }
    }
    Ok(())
}

fn numeric_operand(value: &Value) -> Option<f64> {
    value.as_f64().or_else(|| value.as_bool().map(|b| if b { 1.0 } else { 0.0 }))
}

fn composition(contract: &Object, answers: &Object) -> Checked<Value> {
    if let Some(policy) = contract.get("composition") {
        let policy = object(policy)?;
        for rule in field(policy, "rules")?.as_array().ok_or("Invalid rules")? {
            let rule = object(rule)?;
            let actual = field(object(&answers[string(rule, "question")?])?, "value")?;
            let expected = field(rule, "value")?;
            let numeric = numeric_operand(actual).zip(numeric_operand(expected));
            let matched = match string(rule, "operator")? {
                "eq" => numeric.map_or(actual == expected, |(a,b)| a == b),
                "gte" => numeric.is_some_and(|(a,b)| a >= b),
                "lte" => numeric.is_some_and(|(a,b)| a <= b),
                _ => false,
            };
            if matched { return Ok(field(rule, "result")?.clone()); }
        }
        return Ok(field(policy, "default")?.clone());
    }
    let answer = answers.values().next().ok_or("Missing implicit choice answer")?;
    Ok(field(object(answer)?, "value")?.clone())
}

fn validate_provider(receipt: &Object, contract: &Object) -> Checked<()> {
    let provider = string(receipt, "provider")?;
    let requested = string(receipt, "requested_model")?;
    let resolved = string(receipt, "resolved_model")?;
    let model = string(contract, "model")?;
    require(!requested.is_empty() && !resolved.is_empty() && requested.len() <= 128 && resolved.len() <= 128, "Invalid provider model label")?;
    match provider {
        "mock" => require(requested == model && resolved == "mock", "Invalid declared mock receipt")?,
        "typesafe" => require(requested == model && (model == "jev-latest" || resolved == model), "Provider model mismatch")?,
        "mcp" => {
            let metadata = object(field(receipt, "provider_metadata")?)?;
            let fallback = field(metadata, "fallback_used")?.as_bool().ok_or("Missing explicit MCP fallback evidence")?;
            if fallback {
                // The normalized receipt does not retain negotiated capability details.
                // Require its explicit fallback identity; never reinterpret it as the pinned primary.
                let service = string(metadata, "service_provider")?;
                require(!service.is_empty() && requested == resolved && requested != "jev-latest", "Ambiguous MCP fallback identity")?;
            } else {
                require(requested == resolved && (model == "jev-latest" || resolved == model), "MCP primary model mismatch")?;
            }
        }
        _ => return Err("Unsupported receipt provider".into()),
    }
    if let Some(elapsed) = receipt.get("provider_elapsed_ms").filter(|v| !v.is_null()) {
        require(finite(elapsed)? >= 0.0, "Invalid provider elapsed time")?;
    }
    if let Some(usage) = receipt.get("usage").filter(|v| !v.is_null()) {
        let usage = object(usage)?;
        for name in ["input_tokens", "output_tokens"] {
            if let Some(count) = usage.get(name).filter(|v| !v.is_null()) {
                require(count.as_u64().is_some(), "Invalid provider usage counter")?;
            }
        }
    }
    if let Some(metadata) = receipt.get("provider_metadata").filter(|v| !v.is_null()) { object(metadata)?; }
    Ok(())
}

/// Validate and replay an already-retained normalized receipt. Does not infer or execute effects.
/// `state` is original state.data, matching `jev --state-file`; source locators remain unverified.
pub fn replay(projection: &Projection, contract: &Value, state: &Value, receipt: &Value) -> Checked<Value> {
    validate_projection(projection)?;
    let normalized = normalize_contract(contract)?;
    let contract = object(&normalized)?;
    let r = object(receipt)?;
    allowed(r, &["schema_version", "contract_id", "contract_version", "contract_sha256", "state_sha256", "state_reference", "provider", "requested_model", "resolved_model", "answers", "usage", "provider_elapsed_ms", "provider_metadata", "composition"])?;
    require(string(r, "schema_version")? == "jev-cli/receipt-v1", "Unsupported receipt version")?;
    require(string(r, "contract_id")? == string(contract, "id")? && string(r, "contract_version")? == string(contract, "version")?, "Receipt contract identity mismatch")?;
    require(string(r, "contract_sha256")? == hash_json(&normalized)? && string(r, "state_sha256")? == hash_json(state)?, "Receipt source hash mismatch")?;
    if let Some(reference) = r.get("state_reference").filter(|v| !v.is_null()) { require(reference.is_string(), "Invalid receipt source reference")?; }
    let questions = object(field(contract, "questions")?)?;
    let answers = object(field(r, "answers")?)?;
    validate_answers(answers, questions)?;
    validate_provider(r, contract)?;
    let computed = composition(contract, answers)?;
    require(field(r, "composition")? == &computed, "Receipt composition mismatch")?;
    let disposition = computed.as_str().ok_or("Method requires string composition")?;
    let handler = projection.branches.get(disposition).unwrap_or(&projection.default_handler);
    let output_disposition = match handler.as_str() {
        "jev_return_decision" => disposition,
        "jev_needs_evidence" => "needs_evidence",
        "jev_unknown_route" => "unknown_no_match",
        _ => return Err("Unsupported projected handler".into()),
    };
    Ok(json!({
        "schema_version": "jev-cli/skill-replay-v1",
        "artifact_sha256": projection.artifact_sha256,
        "inference_attempted": false,
        "authority_granted": false,
        "selected_branch": handler,
        "output": { "receipt": receipt, "disposition": output_disposition }
    }))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{fs, path::PathBuf};

    fn fixture() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../integrations/pipelex")
    }

    #[test]
    fn project_is_deterministic_and_verifies_original_source() {
        let projection = project(&fixture()).unwrap();
        assert_eq!(projection, project(&fixture()).unwrap());
        assert_eq!(projection.branches["ready"], "jev_return_decision");
        assert_eq!(projection.default_handler, "jev_unknown_route");
        verify(&projection, &fixture()).unwrap();
    }

    #[test]
    fn altered_source_is_detected() {
        let dir = tempfile::tempdir().unwrap();
        for file in ["SKILL.md", "decision.mthds", "jev_method.py"] {
            fs::copy(fixture().join(file), dir.path().join(file)).unwrap();
        }
        let projection = project(dir.path()).unwrap();
        fs::write(dir.path().join("SKILL.md"), "changed guide").unwrap();
        assert!(verify(&projection, dir.path()).is_err());
        assert_ne!(projection.artifact_sha256, project(dir.path()).unwrap().artifact_sha256);
    }

    fn copied_fixture() -> tempfile::TempDir {
        let dir = tempfile::tempdir().unwrap();
        for file in SOURCE_FILES {
            fs::copy(fixture().join(file), dir.path().join(file)).unwrap();
        }
        dir
    }

    #[test]
    fn rejects_modified_python_without_executing_it() {
        let dir = copied_fixture();
        fs::write(dir.path().join("jev_method.py"), "raise Exception('must never execute')").unwrap();
        assert_eq!(project(dir.path()).unwrap_err(), "Unqualified adapter source");
    }

    #[test]
    fn rejects_unsupported_operators_fields_wiring_cycles_and_extra_nodes() {
        let source = fs::read_to_string(fixture().join("decision.mthds")).unwrap();
        let mutations = [
            source.replace("PipeSequence", "PipeParallel"),
            source.replace("decision.disposition", "decision.receipt.composition"),
            source.replace("result = \"decision\"", "result = \"wrong\""),
            source.replace("pipe = \"route_decision\"", "pipe = \"evaluate_and_route\""),
            source.replace("structure = \"DecisionInput\"", "structure = \"OtherInput\""),
            source.replace("packet = \"DecisionInput\"", "other = \"DecisionInput\""),
            source.replace("function_name = \"jev_return_decision\"", "function_name = \"run_shell\""),
            source.replace("default_outcome = \"return_unknown\"", "default_outcome = \"missing\""),
            format!("{source}\n[pipe.unreachable]\ntype = \"PipeFunc\"\n"),
            format!("{source}\nnew_semantic_field = true\n"),
        ];
        for method in mutations {
            let dir = copied_fixture();
            fs::write(dir.path().join("decision.mthds"), method).unwrap();
            assert!(project(dir.path()).is_err());
        }
    }

    #[test]
    fn consistent_pipe_renaming_preserves_compiled_semantics() {
        let dir = copied_fixture();
        let method = fs::read_to_string(dir.path().join("decision.mthds")).unwrap()
            .replace("evaluate_and_route", "main")
            .replace("evaluate_contract", "evaluate_contract_v2")
            // The registered Python function name is fixed even though graph node names vary.
            .replace("jev_evaluate_contract_v2", "jev_evaluate_contract")
            .replace("route_decision", "dispatch")
            .replace("return_ready", "done");
        fs::write(dir.path().join("decision.mthds"), method).unwrap();
        let projection = project(dir.path()).unwrap();
        assert_eq!(projection.entrypoint, "main");
        assert_eq!(projection.branches, project(&fixture()).unwrap().branches);
    }

    #[test]
    fn every_pipe_requires_its_pipelex_description() {
        let source = fs::read_to_string(fixture().join("decision.mthds")).unwrap();
        let method: toml::Value = toml::from_str(&source).unwrap();
        for name in method["pipe"].as_table().unwrap().keys() {
            let dir = copied_fixture();
            let mut missing = method.clone();
            missing["pipe"][name].as_table_mut().unwrap().remove("description");
            fs::write(dir.path().join("decision.mthds"), toml::to_string(&missing).unwrap()).unwrap();
            assert!(project(dir.path()).is_err(), "accepted a node without required description");
        }
    }

    #[test]
    fn rejects_invalid_domain_and_consistently_renamed_pipe_codes() {
        let source = fs::read_to_string(fixture().join("decision.mthds")).unwrap();
        let method: toml::Value = toml::from_str(&source).unwrap();
        for domain in ["not a valid domain!", "bad-domain", "UPPER", "1domain", "x..y", ".x", "x.", "x\n"] {
            let dir = copied_fixture();
            let mut invalid = method.clone();
            invalid["domain"] = toml::Value::String(domain.into());
            fs::write(dir.path().join("decision.mthds"), toml::to_string(&invalid).unwrap()).unwrap();
            assert!(project(dir.path()).is_err(), "accepted an invalid domain");
        }
        fn replace_refs(value: &mut toml::Value, old: &str, new: &str) {
            match value {
                toml::Value::String(s) if s == old => *s = new.into(),
                toml::Value::Array(values) => { for v in values { replace_refs(v, old, new); } },
                toml::Value::Table(values) => { for (_, v) in values.iter_mut() { replace_refs(v, old, new); } },
                _ => {},
            }
        }
        for name in method["pipe"].as_table().unwrap().keys() {
            for invalid_name in ["invalid name!", "not_snakeCase", "bad-name", "a.b", "1pipe", "_pipe", "pipe\n"] {
                let dir = copied_fixture();
                let mut invalid = method.clone();
                let pipe = invalid["pipe"].as_table_mut().unwrap();
                let renamed = pipe.remove(name).unwrap();
                pipe.insert(invalid_name.into(), renamed);
                replace_refs(&mut invalid, name, invalid_name);
                fs::write(dir.path().join("decision.mthds"), toml::to_string(&invalid).unwrap()).unwrap();
                assert!(project(dir.path()).is_err(), "accepted an invalid pipe code");
            }
        }
    }

    fn packet(probability: f64, fallback: &str) -> (Value, Value, Value) {
        let contract = json!({
            "id":"test.branch", "version":"1", "model":"jev-1.13.0",
            "questions":{"evidence":{"type":"noul","instructions":"Is evidence present?"}},
            "composition":{"rules":[{"question":"evidence","operator":"gte","value":0.8,"result":"ready"}],"default":fallback}
        });
        let state = json!({"source":"synthetic"});
        let receipt = json!({
            "schema_version":"jev-cli/receipt-v1", "contract_id":"test.branch", "contract_version":"1",
            "contract_sha256":hash_json(&normalize_contract(&contract).unwrap()).unwrap(),
            "state_sha256":hash_json(&state).unwrap(), "state_reference":"fixture:source",
            "provider":"mock", "requested_model":"jev-1.13.0", "resolved_model":"mock",
            "answers":{"evidence":{"id":"evidence","type":"noul","value":probability}},
            "composition":if probability >= 0.8 { "ready" } else { fallback }, "provider_elapsed_ms":0.0
        });
        (contract, state, receipt)
    }

    #[test]
    fn offline_replay_preserves_receipts_for_all_branches() {
        let projection = project(&fixture()).unwrap();
        for (probability, fallback, expected, handler) in [
            (0.9,"needs_evidence","ready","jev_return_decision"),
            (0.2,"needs_evidence","needs_evidence","jev_needs_evidence"),
            (0.2,"unrepresented","unknown_no_match","jev_unknown_route"),
        ] {
            let (contract, state, receipt) = packet(probability, fallback);
            let replayed = replay(&projection, &contract, &state, &receipt).unwrap();
            assert_eq!(replayed["output"]["receipt"], receipt);
            assert_eq!(replayed["output"]["disposition"], expected);
            assert_eq!(replayed["selected_branch"], handler);
            assert_eq!(replayed["inference_attempted"], false);
            assert_eq!(replayed["authority_granted"], false);
        }
    }

    #[test]
    fn replay_rejects_tampered_artifact_even_without_sources() {
        let mut projection = project(&fixture()).unwrap();
        let (contract, state, receipt) = packet(0.9, "needs_evidence");
        projection.domain = "tampered".into();
        assert!(replay(&projection, &contract, &state, &receipt).is_err());
        projection.branches.insert("ready".into(), "run_shell".into());
        projection.artifact_sha256 = projection_hash(&projection).unwrap();
        assert!(replay(&projection, &contract, &state, &receipt).is_err());
    }

    #[test]
    fn replay_refuses_mismatched_and_incomplete_receipts() {
        let projection = project(&fixture()).unwrap();
        let (contract, state, receipt) = packet(0.9, "needs_evidence");
        for (key, value) in [
            ("contract_sha256", json!("bad")), ("state_sha256", json!("bad")),
            ("contract_id", json!("other")), ("state_reference",json!(false)),
            ("contract_version",json!("2")), ("composition",json!("needs_evidence")),
            ("answers",json!({})), ("requested_model",json!("other")),
            ("resolved_model",json!("not-mock")), ("provider",json!("undeclared")),
            ("provider_elapsed_ms",json!(-1)), ("usage",json!({"input_tokens":-1})),
        ] {
            let mut bad = receipt.clone(); bad[key] = value;
            assert!(replay(&projection, &contract, &state, &bad).is_err(), "accepted mutated {key}");
        }
        for value in [json!(true),json!(-0.1),json!(1.1),json!("0.9")] {
            let mut bad = receipt.clone(); bad["answers"]["evidence"]["value"] = value;
            assert!(replay(&projection, &contract, &state, &bad).is_err());
        }
    }

    #[test]
    fn direct_and_mcp_model_checks_preserve_explicit_fallbacks() {
        let projection = project(&fixture()).unwrap();
        let (contract, state, mut receipt) = packet(0.9,"needs_evidence");
        receipt["provider"] = json!("typesafe"); receipt["resolved_model"] = json!("jev-1.13.0");
        replay(&projection, &contract, &state, &receipt).unwrap();
        receipt["resolved_model"] = json!("jev-other");
        assert!(replay(&projection, &contract, &state, &receipt).is_err());
        receipt["provider"] = json!("mcp"); receipt["requested_model"] = json!("bounded/fallback"); receipt["resolved_model"] = json!("bounded/fallback");
        assert!(replay(&projection, &contract, &state, &receipt).is_err());
        receipt["provider_metadata"] = json!({"fallback_used":true,"service_provider":"openrouter"});
        replay(&projection, &contract, &state, &receipt).unwrap();
        receipt["provider_metadata"]["fallback_used"] = json!(false);
        assert!(replay(&projection, &contract, &state, &receipt).is_err());
    }

    #[test]
    fn validates_choice_and_score_distribution_semantics() {
        let questions = json!({
            "choice":{"type":"choice","instructions":"select","criteria":{"x":"X","y":"Y"}},
            "score":{"type":"score","instructions":"score","criteria":["low","mid","high"]}
        });
        let answers = json!({
            "choice":{"id":"choice","type":"choice","value":"x","probabilities":{"x":0.8,"y":0.2},"confidence":0.6},
            "score":{"id":"score","type":"score","value":1.4,"probabilities":{"0":0.1,"1":0.4,"2":0.5},"confidence":0.5}
        });
        validate_answers(object(&answers).unwrap(), object(&questions).unwrap()).unwrap();
        for (path, value) in [
            ("/choice/value",json!("y")), ("/choice/probabilities/x",json!(0.5)),
            ("/score/value",json!(1.8)), ("/score/confidence",json!(true)),
            ("/choice/id",json!("mismatch")), ("/score/type",json!("noul")),
        ] {
            let mut bad = answers.clone(); *bad.pointer_mut(path).unwrap() = value;
            assert!(validate_answers(object(&bad).unwrap(), object(&questions).unwrap()).is_err());
        }
    }

    #[test]
    fn canonical_json_matches_python_numbers_and_unicode() {
        let value: Value = serde_json::from_str(r#"{"z": [1e-7,1e-5,1e-4,1e15,1e16,1e20,-0.0,1.0],"a":"Δ🌙\n","nested":{"z":null,"a":true}}"#).unwrap();
        assert_eq!(canonical(&value).unwrap(), "{\"a\":\"Δ🌙\\n\",\"nested\":{\"a\":true,\"z\":null},\"z\":[1e-07,1e-05,0.0001,1000000000000000.0,1e+16,1e+20,-0.0,1.0]}");
        let huge: Value = serde_json::from_str("18446744073709551616").unwrap();
        assert!(canonical(&huge).is_err());
        let overflow: Value = serde_json::from_str("1e999").unwrap();
        assert!(canonical(&overflow).is_err());
        assert_eq!(canonical(&serde_json::from_str::<Value>("-0").unwrap()).unwrap(), "0");
    }
}
