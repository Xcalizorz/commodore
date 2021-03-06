"""
Tests for command line interface (CLI)
"""
from subprocess import call


def test_runas_module():
    """
    Can this package be run as a Python module?
    """
    exit_status = call("python -m commodore", shell=True)
    assert exit_status == 0


def test_entrypoint():
    """
    Is entrypoint script installed?
    """
    exit_status = call("commodore --help", shell=True)
    assert exit_status == 0


def test_clean_command():
    """
    Is subcommand available?
    """
    exit_status = call("commodore catalog clean --help", shell=True)
    assert exit_status == 0


def test_compile_command():
    """
    Is subcommand available?
    """
    exit_status = call("commodore catalog compile --help", shell=True)
    assert exit_status == 0


def test_component_new_command():
    """
    Is subcommand available?
    """
    exit_status = call("commodore component new --help", shell=True)
    assert exit_status == 0


def test_component_compile_command():
    """
    Is subcommand available?
    """
    exit_status = call("commodore component compile --help", shell=True)
    assert exit_status == 0
