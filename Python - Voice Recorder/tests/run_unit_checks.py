import sys
import os

# Ensure tests package directory is importable when running directly
tests_dir = os.path.dirname(__file__)
project_root = os.path.dirname(tests_dir)
# Ensure tests directory and project root are importable
for p in (tests_dir, project_root):
    if p not in sys.path:
        sys.path.insert(0, p)

import test_utils_and_recording_helpers as test_module
test_recording_utils_sha256_and_size_and_filename = test_module.test_recording_utils_sha256_and_size_and_filename
test_to_dict_handles_primitives_and_dates = test_module.test_to_dict_handles_primitives_and_dates


def main():
    try:
        test_recording_utils_sha256_and_size_and_filename()
        test_to_dict_handles_primitives_and_dates()
    except AssertionError as e:
        print("Tests failed:", e)
        return 2
    except Exception as e:
        print("Error running tests:", type(e).__name__, e)
        return 3
    print("All checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
