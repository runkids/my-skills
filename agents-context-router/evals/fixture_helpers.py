"""Shared synthetic-file and router subprocess primitives for eval fixtures."""
import os
import subprocess
import sys


def write_fixture(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def run_router(script, *args, overrides=None, cwd=None):
    env = {key: value for key, value in os.environ.items()
           if key not in ('AI_CONTEXT_ROOT', 'AI_CONTEXT_CONFIG')}
    env.update(overrides or {})
    return subprocess.run([sys.executable, str(script), *args], env=env,
                          cwd=cwd, capture_output=True, encoding='utf-8')
