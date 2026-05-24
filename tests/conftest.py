def pytest_addoption(parser):
    parser.addoption(
        "--regen-goldens",
        action="store_true",
        default=False,
        help="Regenerate the golden JSON files in tests/goldens/ from the current source.",
    )
