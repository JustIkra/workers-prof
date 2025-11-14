"""
Service for loading and managing metric label-to-code mappings from YAML configuration.

Provides mapping from extracted metric labels (from documents) to internal MetricDef codes.
"""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class MetricMappingService:
    """
    Service for managing metric label-to-code mappings.

    Loads YAML configuration and provides lookup methods for mapping
    extracted labels to metric codes.
    """

    def __init__(self, config_path: str | Path | None = None):
        """
        Initialize metric mapping service.

        Args:
            config_path: Path to YAML configuration file.
                        Defaults to config/app/metric-mapping.yaml
        """
        if config_path is None:
            # Default path relative to project root
            # Try multiple possible locations:
            # 1. In Docker: /app/app/services/metric_mapping.py -> /app/config/app/metric-mapping.yaml
            # 2. In local dev: api-gateway/app/services/metric_mapping.py -> ../config/app/metric-mapping.yaml
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "app" / "metric-mapping.yaml"
            
            # If not found, try parent directory (for local dev where api-gateway is a subdirectory)
            if not config_path.exists() and project_root.name == "api-gateway":
                config_path = project_root.parent / "config" / "app" / "metric-mapping.yaml"
        else:
            config_path = Path(config_path)

        self.config_path = config_path
        self._mappings: dict[str, dict[str, str]] = {}
        self._loaded = False

    def load(self) -> None:
        """
        Load mappings from YAML configuration file.

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            yaml.YAMLError: If YAML parsing fails
            ValueError: If configuration structure is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Metric mapping config not found: {self.config_path}")

        logger.info(f"Loading metric mappings from {self.config_path}")

        with open(self.config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise ValueError(f"Invalid config structure: expected dict, got {type(config)}")

        if "report_mappings" not in config:
            raise ValueError("Missing 'report_mappings' key in config")

        report_mappings = config["report_mappings"]
        if not isinstance(report_mappings, dict):
            raise ValueError(
                f"Invalid report_mappings structure: expected dict, got {type(report_mappings)}"
            )

        # Parse and validate mappings for each report type
        self._mappings = {}
        for report_type, mapping_config in report_mappings.items():
            if not isinstance(mapping_config, dict):
                logger.warning(
                    f"Skipping invalid mapping config for {report_type}: "
                    f"expected dict, got {type(mapping_config)}"
                )
                continue

            header_map = mapping_config.get("header_map", {})
            if not isinstance(header_map, dict):
                logger.warning(
                    f"Skipping invalid header_map for {report_type}: "
                    f"expected dict, got {type(header_map)}"
                )
                continue

            # Store normalized mapping (uppercase keys)
            self._mappings[report_type] = {
                label.upper().strip(): code.strip() for label, code in header_map.items()
            }

            logger.info(
                f"Loaded {len(self._mappings[report_type])} mappings for report type {report_type}"
            )

        self._loaded = True
        logger.info(f"Successfully loaded mappings for {len(self._mappings)} report types")

    def get_metric_code(self, report_type: str, label: str) -> str | None:
        """
        Get metric code for a given label and report type.

        Args:
            report_type: Report type (e.g., "REPORT_1", "REPORT_2", "REPORT_3")
            label: Metric label from document (will be normalized to uppercase)

        Returns:
            Metric code if found, None otherwise
        """
        if not self._loaded:
            self.load()

        # Normalize label
        normalized_label = label.upper().strip()

        # Get mapping for report type
        report_mapping = self._mappings.get(report_type, {})
        return report_mapping.get(normalized_label)

    def get_report_mapping(self, report_type: str) -> dict[str, str]:
        """
        Get all mappings for a specific report type.

        Args:
            report_type: Report type (e.g., "REPORT_1", "REPORT_2", "REPORT_3")

        Returns:
            Dictionary of label -> metric_code mappings
        """
        if not self._loaded:
            self.load()

        return self._mappings.get(report_type, {}).copy()

    def get_all_mappings(self) -> dict[str, dict[str, str]]:
        """
        Get all mappings for all report types.

        Returns:
            Dictionary of report_type -> {label -> metric_code}
        """
        if not self._loaded:
            self.load()

        return {report_type: mapping.copy() for report_type, mapping in self._mappings.items()}

    def get_supported_report_types(self) -> list[str]:
        """
        Get list of supported report types.

        Returns:
            List of report type identifiers
        """
        if not self._loaded:
            self.load()

        return list(self._mappings.keys())

    def reload(self) -> None:
        """Reload mappings from configuration file."""
        logger.info("Reloading metric mappings")
        self._loaded = False
        self._mappings = {}
        self.load()


# Global singleton instance
_mapping_service: MetricMappingService | None = None


def get_metric_mapping_service(config_path: str | Path | None = None) -> MetricMappingService:
    """
    Get global MetricMappingService instance.

    Args:
        config_path: Optional path to configuration file (only used on first call)

    Returns:
        MetricMappingService instance
    """
    global _mapping_service
    if _mapping_service is None:
        _mapping_service = MetricMappingService(config_path)
        _mapping_service.load()
    return _mapping_service
