"""Tests in this file validate `CLI` located at `src/agentic_tdd_linter/cli/main.py`.
`CLI` is responsible for providing the create-agent-md and lint command interface.

Terms:
- `CLI output`: CLI output is the text printed for a command result. For example, it reports lint issues or the number of recorded attestations.
- `.agent.md`: An .agent.md file contains one review scorecard that create-agent-md generates. For example, packet creation writes one file for each test.
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agentic_tdd_linter.cli.main import main



class CliTests(unittest.TestCase):
    def test_test_root_reports_generated_packet(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `CLI` emits `CLI output` containing the generated `.agent.md` count when a caller runs create-agent-md with a nondefault test root.
        Specialized usage: For generated fixtures, CLI configures temporary_fixtures as the test root instead of the default root.

        Verification Method: verify public function output

        Verification Detail:
        `CLI output` contains the text `generated 2 agent review packets` for one single-test packet and one cross-test packet.

        Similar Coverage:
        - Scenario Difference: `test_main.py::test_lint_reports_only_selected_file`
          Explanation: The current test verifies `CLI` emits `CLI output` with the generated `.agent.md` count when caller selects a nondefault test root. The named test verifies `CLI` restricts `CLI output` to the caller-selected test-file path; both use happy path, but exercise materially different scenarios.
        - Scenario Difference: `test_load_all_formats.py::test_loads_python_tests`
          Explanation: The current test verifies `CLI` emits `CLI output` with the generated `.agent.md` count when caller selects a nondefault test root. The named test verifies `create-agent-md` creates a `packet set` from a discovered `.py` test file; both use happy path, but exercise materially different scenarios.
        """

        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            test_root = repo_root / "temporary_fixtures"
            test_root.mkdir()
            test_file = test_root / "pass_test.py"
            module_file = repo_root / "src" / "addition.py"
            module_file.parent.mkdir()
            module_file.write_text("def add(a, b): return a + b\n", encoding="utf-8")
            test_file.write_text(
                textwrap.dedent(
                    '''
                    """Tests in this file validate `addition` located at `src/addition.py`.
                    `addition` is responsible for calculating numeric sums.
                    """

                    def test_adds_positive_numbers() -> None:
                        """Test Path: happy path

                        Requirement Tested:
                        `addition` calculates sums.
                        When operands contain positive integers, addition calculates sums.

                        Verification Method: verify public function output

                        Verification Detail:
                        The expression produces `3`.
                        """

                        assert 1 + 2 == 3
                    '''
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "create-agent-md",
                        "--repo-root",
                        str(repo_root),
                        "--test-root",
                        str(test_root),
                        str(test_file),
                    ]
                )

        self.assertIn("generated 2 agent review packets", stdout.getvalue())


class ReviewProofFlowTests(unittest.TestCase):
    def test_lint_reports_only_selected_file(self) -> None:
        """Test Path: happy path

        Requirement Tested:
        `CLI` restricts `CLI output` to the caller-selected test-file path.
        Specialized usage: Caller selects one test-file path rather than the full test scope.

        Verification Method: verify public function output

        Verification Detail:
        Harness invokes lint with `test_first.py` as the selected path.
        `CLI output` contains the selected `test_first.py` file.
        `CLI output` omits the other `test_second.py` file.

        Similar Coverage:
        - Scenario Difference: `test_main.py::test_test_root_reports_generated_packet`
          Explanation: The current test verifies `CLI` restricts `CLI output` to the caller-selected test-file path. The named test verifies `CLI` emits `CLI output` with the generated `.agent.md` count when caller selects a nondefault test root; both use happy path, but exercise materially different scenarios.
        """

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / "tests"
            tests.mkdir()
            first = tests / "test_first.py"
            second = tests / "test_second.py"
            source = textwrap.dedent(
                '''
                """Tests in this file validate `examples` located at `src/examples.py`.
                `examples` is responsible for preserving boolean truth.
                """

                def test_example() -> None:
                    """Test Path: happy path

                    Requirement Tested:
                    `examples` preserves truth.
                    When expressions are true, examples preserve truth.

                    Verification Method: verify public function output

                    Verification Detail:
                    The expression equals `True`.
                    """

                    assert True
                '''
            ).strip() + "\n"
            module_file = root / "src" / "examples.py"
            module_file.parent.mkdir()
            module_file.write_text("VALUE = True\n", encoding="utf-8")
            first.write_text(source, encoding="utf-8")
            second.write_text(source, encoding="utf-8")
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "lint",
                        "--fresh",
                        "--repo-root",
                        str(root),
                        str(first),
                    ]
                )

        self.assertIn("test_first.py", stdout.getvalue())
        self.assertNotIn("test_second", stdout.getvalue())


def _valid_test_function_source(name: str) -> str:
    return textwrap.dedent(
        f'''\
        def {name}() -> None:
            """Test Path: happy path

            Requirement Tested:
            `addition` calculates sums.
            When expressions are true, examples preserve truth.

            Verification Method: verify public function output

            Verification Detail:
            The expression equals `True`.
            """

            assert True
        '''
    )



if __name__ == "__main__":
    unittest.main()
