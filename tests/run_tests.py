"""
Simple test runner that executes all test_* functions, handling fixtures and assertions.
"""

import sys
import types
import inspect
from pathlib import Path

# Provide mock pytest if not installed
if "pytest" not in sys.modules:
    mock_pytest = types.ModuleType("pytest")
    mock_pytest.fixture = lambda f: f

    class RaisesContext:
        def __init__(self, expected_exc):
            self.expected_exc = expected_exc
            self.value = None
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.value = exc_val
            if exc_type is None:
                raise AssertionError(f"Expected {self.expected_exc} was not raised.")
            return issubclass(exc_type, self.expected_exc)

    mock_pytest.raises = RaisesContext
    sys.modules["pytest"] = mock_pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

def run():
    test_files = [
        "test_auth",
        "test_ticketing",
        "test_ingest",
        "test_vector_store",
        "test_retrieval",
        "test_generator",
        "test_backend_interface",
        "test_vercel_entrypoint"
    ]

    passed = 0
    failed = 0

    for name in test_files:
        try:
            import importlib
            mod = importlib.import_module(f"tests.{name}")

            # Collect fixtures
            fixtures = {}
            for attr in dir(mod):
                obj = getattr(mod, attr)
                if callable(obj) and not attr.startswith("test_") and not attr.startswith("_"):
                    fixtures[attr] = obj

            for attr in dir(mod):
                if attr.startswith("test_") and callable(getattr(mod, attr)):
                    fn = getattr(mod, attr)
                    sig = inspect.signature(fn)
                    args = []
                    teardowns = []

                    try:
                        for p in sig.parameters.values():
                            if p.name in fixtures:
                                f_res = fixtures[p.name]()
                                if inspect.isgenerator(f_res):
                                    val = next(f_res)
                                    teardowns.append(f_res)
                                    args.append(val)
                                else:
                                    args.append(f_res)

                        fn(*args)
                        print(f"  ✅ {name}.{attr}")
                        passed += 1
                    except Exception as e:
                        print(f"  ❌ {name}.{attr}: {e}")
                        failed += 1
                    finally:
                        for gen in teardowns:
                            try:
                                next(gen)
                            except StopIteration:
                                pass

        except Exception as e:
            print(f"⚠️ Could not load {name}: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed.")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(run())
