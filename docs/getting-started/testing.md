# Testing

This guide defines how to write and structure tests for ModelMora to ensure code quality and reliability.

## Testing Framework

We use `pytest` as our primary testing framework. Make sure you have it installed in your development environment.

## Writing Tests

1. **Type of Tests**:
   - **Unit Tests**: Test individual functions or classes in isolation. Should be placed in the `tests/unit/` directory.
   - **Integration Tests**: Test interactions between different components. Should be placed in the `tests/integration/` directory.
   - **End-to-End Tests**: Simulate real user scenarios to validate the entire application flow. Should be placed in the `tests/e2e/` directory.
2. **Directory Structure**:
   - Organize tests in a directory structure that mirrors the application structure for easier navigation.
3. **Naming Conventions**:
   - Test files should be named with a `test_` prefix (e.g., `test_module.py`).
   - Test functions should also start with `test_` (e.g., `def test_function():`).
   - Use descriptive names for test functions to indicate their purpose. The name should specify the expected behavior or condition being tested. Examples: `def test_add_user_with_valid_data_should_succeed():`, `def test_calculate_discount_with_invalid_input_should_raise_error():`, `def test_process_payment_with_insufficient_funds_should_fail():`.
4. **Assertions**:
   - Use clear and specific assertions to validate expected outcomes. Prefer using `assert` statements provided by `pytest`.
   - Example: `assert result == expected_value`
   - For exception testing, use `with pytest.raises(ExpectedException):`.
5. **Structure of a Test**:
   - Arrange: Set up the necessary preconditions and inputs.
   - Act: Execute the code being tested.
   - Assert: Verify that the outcome matches the expected result.
6. **Fixtures**:
   - Use `pytest` fixtures to set up and tear down test environments. This helps in reusing code and maintaining clean tests.
   - Example:

     ```python
     @pytest.fixture
     def sample_data():
         return {"key": "value"}
     ```

7. **Clear Bugs**:
   - If, when running tests, you find clear bugs in the code, and only if it is clear that the fix is straightforward and does not require extensive discussion or design changes, please feel free to fix the implementation directly.

## Coverage

We use `pytest-cov` to measure code coverage. The goal is to maintain close to 99% coverage across the codebase.

## Running Tests

The tests can be executed through VS Code's testing interface if available, with coverage support showing which lines are covered by tests. Alternatively, you can run tests from the command line:

```bash
./.venv/bin/poetry run pytest tests # Linux / MacOS
```

```powershell
.\.venv\Scripts\poetry run pytest tests # Windows
```

Do not forget to use the .venv environment to ensure all dependencies are correctly resolved.
