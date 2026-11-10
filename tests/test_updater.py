import pytest
from unittest.mock import patch, MagicMock
from src.updater import (
    get_latest_aur_version,
    get_latest_pypi_version,
    detect_install_method,
    check_for_updates,
    get_version_status,
    update_aur,
    update_pip,
)


def test_get_latest_aur_version_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [{"Version": "2.1.1-1"}]
    }
    with patch("requests.get", return_value=mock_resp):
        ver = get_latest_aur_version()
        assert ver == "2.1.1"


def test_get_latest_aur_version_empty_or_fail():
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch("requests.get", return_value=mock_resp):
        assert get_latest_aur_version() is None


def test_detect_install_method():
    with patch("src.updater.is_bundled", return_value=False):
        with patch("pathlib.Path.resolve") as mock_resolve:
            mock_path = MagicMock()
            mock_path.as_posix.return_value = "/usr/lib/python3.12/site-packages/ani_cli_arabic/updater.py"
            mock_resolve.return_value = mock_path
            with patch("platform.system", return_value="Linux"):
                with patch("subprocess.run") as mock_sub:
                    mock_sub.return_value.returncode = 0
                    assert detect_install_method() == "aur"


def test_aur_does_not_update_when_aur_is_not_bumped():
    # PyPI has 2.1.1, AUR has 2.1.0, current is 2.1.0
    with patch("src.updater.detect_install_method", return_value="aur"):
        with patch("src.updater.get_latest_aur_version", return_value="2.1.0"):
            with patch("src.updater.__version__", "2.1.0"):
                # Should detect as up-to-date since AUR is only 2.1.0
                assert check_for_updates(auto_update=True, interactive=False) is False


def test_aur_update_available_when_aur_is_bumped():
    with patch("src.updater.detect_install_method", return_value="aur"):
        with patch("src.updater.get_latest_aur_version", return_value="2.1.1"):
            with patch("src.updater.__version__", "2.1.0"):
                # Non-interactive check should just report True without running commands
                with patch("src.updater.update_aur") as mock_update_aur:
                    mock_update_aur.return_value = False
                    # auto_update=False
                    assert check_for_updates(auto_update=False, interactive=False) is True
                    mock_update_aur.assert_not_called()


def test_update_aur_non_interactive():
    # In non-interactive mode (e.g. background check), it should never run subprocess
    with patch("shutil.which", return_value="/usr/bin/yay"):
        with patch("subprocess.run") as mock_sub:
            res = update_aur("2.1.1", interactive=False)
            assert res is False
            mock_sub.assert_not_called()


def test_update_aur_interactive_confirm():
    with patch("shutil.which", return_value="/usr/bin/yay"):
        with patch("builtins.input", return_value="y"):
            with patch("subprocess.run") as mock_sub:
                mock_sub.return_value.returncode = 0
                with pytest.raises(SystemExit) as exc_info:
                    update_aur("2.1.1", interactive=True)
                assert exc_info.value.code == 0
                mock_sub.assert_called_once_with(["yay", "-S", "ani-cli-arabic"])


def test_update_aur_interactive_decline():
    with patch("shutil.which", return_value="/usr/bin/yay"):
        with patch("builtins.input", return_value="n"):
            with patch("subprocess.run") as mock_sub:
                res = update_aur("2.1.1", interactive=True)
                assert res is False
                mock_sub.assert_not_called()


def test_get_version_status_aur():
    with patch("src.updater.detect_install_method", return_value="aur"):
        with patch("src.updater.get_latest_aur_version", return_value="2.1.1"):
            with patch("src.updater.__version__", "2.1.0"):
                status = get_version_status()
                assert status is not None
                assert status["current"] == "2.1.0"
                assert status["latest"] == "2.1.1"
                assert status["is_outdated"] is True
                assert status["install_method"] == "aur"


def test_update_aur_force():
    with patch("shutil.which", return_value="/usr/bin/yay"):
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value.returncode = 0
            res = update_aur("2.1.4", interactive=False, force=True)
            assert res is True
            mock_sub.assert_called_once_with(["yay", "-S", "--noconfirm", "ani-cli-arabic"])


def test_update_pip_force():
    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value.returncode = 0
        res = update_pip("2.1.4", interactive=False, force=True)
        assert res is True
        assert mock_sub.called


def test_perform_auto_update_skips_source():
    from src.updater import perform_auto_update
    with patch("src.updater.detect_install_method", return_value="source"):
        assert perform_auto_update() is False


def test_perform_auto_update_executes_on_newer_version():
    from src.updater import perform_auto_update
    with patch("src.updater.detect_install_method", return_value="pip"):
        with patch("src.updater.get_latest_pypi_version", return_value="9.9.9"):
            with patch("src.updater.__version__", "2.1.3"):
                with patch("src.updater.update_pip", return_value=True) as mock_update_pip:
                    res = perform_auto_update()
                    assert res is True
                    mock_update_pip.assert_called_once_with("9.9.9", interactive=False, force=True)


