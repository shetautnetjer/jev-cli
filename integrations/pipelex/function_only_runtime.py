"""Boot a function-only method without configuring a second inference provider.

Pipelex's public model-manager injection point deliberately refuses PipeLLM and
other native inference here. The caller supplies Jev through bind_provider().
"""

from typing import Any

from jev_method import register_pipelex
from pipelex.cogt.models.model_manager_abstract import ModelManagerAbstract
from pipelex.pipelex import Pipelex


class FunctionOnlyModels(ModelManagerAbstract):
    def setup(self, **kwargs: Any) -> None:
        pass

    def validate_model_deck(self) -> None:
        pass

    def teardown(self) -> None:
        pass

    def get_inference_model(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            "This pilot uses host-bound Jev; native Pipelex inference is unavailable"
        )

    def get_model_deck(self) -> Any:
        raise RuntimeError("This pilot has no Pipelex model deck")

    def get_required_inference_backend(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("This pilot has no Pipelex inference backend")


def boot() -> None:
    """Call from the pilot directory; its backend file enables only software code."""
    Pipelex.make(
        needs_inference=True,
        needs_model_specs=False,
        models_manager=FunctionOnlyModels(),
        library_dirs=[],
        config_overrides={
            "runtime": {
                "log": {
                    "default_log_level": "ERROR",
                    "pretty_print_mode": "silent",
                    # Pipelex's error logs include complete inputs; the runner returns
                    # a sanitized error class instead of logging private source text.
                    "package_log_levels": {"pipelex": "CRITICAL"},
                },
                "tracing": {"is_enabled": False},
            },
            "interpreter": {
                "pipeline_execution": {"is_generate_graph": False, "is_generate_usage": False}
            },
        },
    )
    register_pipelex()
