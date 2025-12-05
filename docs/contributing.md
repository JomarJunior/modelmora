# Contributing

Thank you for considering contributing to ModelMora!

## Development Setup

1. Fork and clone the repository
2. Install dependencies: `poetry install --with dev,docs`
3. Install pre-commit hooks: `poetry run pre-commit install`
4. Create a feature branch: `git checkout -b feature/my-feature`

## Code Standards

- **Formatting**: Black (120 char line length)
- **Linting**: Pylint, isort
- **Type Checking**: MyPy
- **Testing**: pytest (>70% coverage required)

## Pull Request Process

1. Write tests for new features
2. Ensure all tests pass: `poetry run pytest`
3. Format code: `poetry run black . && poetry run isort .`
4. Run linters: `poetry run pylint src/modelmora`
5. Update documentation as needed
6. Submit PR with clear description

## Commit Messages

Follow conventional commits:

```bash
feat: add model warmup feature
fix: resolve memory leak in worker cleanup
docs: update API reference
test: add integration test for lifecycle
```

## Questions?

Open an issue or discussion on GitHub.
