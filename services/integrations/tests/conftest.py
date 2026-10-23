"""Каталог файлов тестов задаётся до импорта приложения."""

import os
import tempfile

os.environ["INTEGRATIONS_DOCUMENTS_DIR"] = tempfile.mkdtemp(prefix="integrations-docs-")
