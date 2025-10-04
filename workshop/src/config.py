"""
Workshop Configuration Management
Handles reading/writing ~/.workshop/config.json for per-project settings
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional, Any


class WorkshopConfig:
    """Manages Workshop configuration file"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config manager.

        Args:
            config_path: Path to config file. Defaults to ~/.workshop/config.json
        """
        self.config_path = config_path or (Path.home() / '.workshop' / 'config.json')
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load config from file, creating with defaults if doesn't exist"""
        if not self.config_path.exists():
            return self._create_default_config()

        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If config is corrupted, backup and recreate
            backup_path = self.config_path.with_suffix('.json.backup')
            if self.config_path.exists():
                self.config_path.rename(backup_path)
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        config = {
            "version": "1.0",
            "default_mode": "per-project",
            "projects": {},
            "global": {
                "database": str(Path.home() / '.workshop' / 'workshop.db'),
                "enabled": False
            }
        }
        self._save_config(config)
        return config

    def _save_config(self, config: Optional[Dict[str, Any]] = None):
        """Save config to file"""
        if config is None:
            config = self._config

        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)

    def get_project_config(self, project_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific project.

        Args:
            project_path: Absolute path to project

        Returns:
            Project config dict or None if not registered
        """
        project_key = str(project_path.resolve())
        return self._config.get('projects', {}).get(project_key)

    def register_project(
        self,
        project_path: Path,
        database_path: Optional[Path] = None,
        jsonl_path: Optional[Path] = None,
        auto_import: bool = True
    ) -> Dict[str, Any]:
        """
        Register a project in the config.

        Args:
            project_path: Absolute path to project
            database_path: Path to database file (defaults to project/.workshop/workshop.db)
            jsonl_path: Path to JSONL directory (auto-detected if None)
            auto_import: Whether to auto-import new JSONL files

        Returns:
            Project config dict
        """
        project_key = str(project_path.resolve())

        # Auto-detect paths if not provided
        if database_path is None:
            database_path = project_path / '.workshop' / 'workshop.db'

        if jsonl_path is None:
            # Auto-detect Claude Code JSONL location
            norm_path = str(project_path).replace('/', '-').replace('_', '-')
            jsonl_path = Path.home() / '.claude' / 'projects' / norm_path

        project_config = {
            "database": str(database_path),
            "jsonl_path": str(jsonl_path),
            "auto_import": auto_import,
            "registered_at": str(Path.cwd())  # Track where it was registered from
        }

        if 'projects' not in self._config:
            self._config['projects'] = {}

        self._config['projects'][project_key] = project_config
        self._save_config()

        return project_config

    def unregister_project(self, project_path: Path) -> bool:
        """
        Remove a project from the config.

        Args:
            project_path: Absolute path to project

        Returns:
            True if project was removed, False if not found
        """
        project_key = str(project_path.resolve())

        if project_key in self._config.get('projects', {}):
            del self._config['projects'][project_key]
            self._save_config()
            return True

        return False

    def list_projects(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered projects"""
        return self._config.get('projects', {})

    def get_global_config(self) -> Dict[str, Any]:
        """Get global Workshop configuration"""
        return self._config.get('global', {})

    def set_global_enabled(self, enabled: bool):
        """Enable/disable global Workshop mode"""
        if 'global' not in self._config:
            self._config['global'] = {}
        self._config['global']['enabled'] = enabled
        self._save_config()

    def validate(self) -> Dict[str, Any]:
        """
        Validate configuration and return status.

        Returns:
            Dict with validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Check each project
        for project_path, project_config in self._config.get('projects', {}).items():
            # Check if project path exists
            if not Path(project_path).exists():
                results['warnings'].append(f"Project path does not exist: {project_path}")

            # Check database path
            db_path = Path(project_config.get('database', ''))
            if not db_path.parent.exists():
                results['errors'].append(f"Database directory does not exist: {db_path.parent}")
                results['valid'] = False

            # Check JSONL path
            jsonl_path = Path(project_config.get('jsonl_path', ''))
            if not jsonl_path.exists():
                results['warnings'].append(f"JSONL directory not found: {jsonl_path}")

        return results

    def get_raw_config(self) -> Dict[str, Any]:
        """Get the raw config dictionary for editing"""
        return self._config.copy()

    def update_from_dict(self, new_config: Dict[str, Any]):
        """Update config from a dictionary (validates first)"""
        # Basic validation
        if 'version' not in new_config:
            raise ValueError("Config must have a 'version' field")

        if 'projects' in new_config and not isinstance(new_config['projects'], dict):
            raise ValueError("'projects' must be a dictionary")

        self._config = new_config
        self._save_config()
