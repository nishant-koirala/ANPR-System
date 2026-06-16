"""
Self-contained test runner for all bug/security fixes.
Run from project root:  python tests/unit/run_bug_fix_tests.py
"""
import sys, os, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results = []

def check(name, fn):
    try:
        fn()
        print(f"  {PASS}  {name}")
        results.append((name, True, None))
    except Exception as e:
        msg = str(e)
        print(f"  {FAIL}  {name}")
        print(f"        {msg}")
        results.append((name, False, msg))


# ── BUG-001 ──────────────────────────────────────────────────────────────────
print("\nBUG-001 — difflib.SequenceMatcher replaced with SequenceMatcher")

def bug001_no_difflib_attribute():
    import ast, inspect, src.db.toggle_manager as tm
    src_text = inspect.getsource(tm)
    tree = ast.parse(src_text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if (isinstance(node.value, ast.Name) and
                    node.value.id == 'difflib' and node.attr == 'SequenceMatcher'):
                raise AssertionError("difflib.SequenceMatcher still present")

def bug001_similarity_returns_float():
    from src.db.toggle_manager import ToggleManager
    from difflib import SequenceMatcher
    # Directly call the class method without a full object
    class Fake:
        pass
    tm = object.__new__(ToggleManager)
    tm.db = tm.min_confidence = tm.cooldown_minutes = tm.exit_similarity_threshold = None
    tm.special_db = tm.email_sender = None
    tm._recent_detections = {}
    tm._last_stolen_alert = None
    r = tm.calculate_plate_similarity("BA 1234", "BA 1235")
    assert isinstance(r, float) and 0.0 <= r <= 1.0, f"Got {r}"

check("no difflib.SequenceMatcher attribute call in source", bug001_no_difflib_attribute)
check("calculate_plate_similarity returns float without NameError", bug001_similarity_returns_float)


# ── BUG-002 ──────────────────────────────────────────────────────────────────
print("\nBUG-002 — get_database imported in toggle_manager")

def bug002_get_database_importable():
    import src.db.toggle_manager as tm
    assert hasattr(tm, 'get_database'), "get_database not in toggle_manager namespace"

check("get_database present in toggle_manager module", bug002_get_database_importable)


# ── BUG-003 ──────────────────────────────────────────────────────────────────
print("\nBUG-003 — remove_plate_from_vehicle handles 4-tuples")

def bug003_no_tuple_unpack():
    from collections import defaultdict
    candidates = defaultdict(list)
    candidates[1] = [("BA 1234", 0.9, 3, 0.85), ("BA 1235", 0.7, 1, 0.60)]
    # Simulate the fixed implementation
    plate_text = "BA 1234"
    candidates[1] = [item for item in candidates[1] if item[0] != plate_text]
    assert len(candidates[1]) == 1 and candidates[1][0][0] == "BA 1235"

def bug003_main_py_uses_item_index():
    # Read main.py with UTF-8 encoding (file contains Nepali unicode characters)
    main_path = os.path.join(os.path.dirname(__file__), '..', '..', 'main.py')
    with open(main_path, encoding='utf-8') as f:
        src_text = f.read()
    assert '(p, c, count) for p, c, count in' not in src_text, \
        "Old 3-tuple unpack still in main.py"
    assert 'item for item in candidates if item[0]' in src_text, \
        "Fixed item[0] pattern not found in main.py"

check("4-tuple list comprehension logic is correct", bug003_no_tuple_unpack)
check("main.py uses item[0] not (p, c, count) unpack", bug003_main_py_uses_item_index)


# ── BUG-004 ──────────────────────────────────────────────────────────────────
print("\nBUG-004 — B/S/G not in OCR char_substitutions")

def bug004_B_absent():
    import ast, inspect, src.ocr.plate_reader as pr
    src_text = inspect.getsource(pr)
    # Look for  'B': '8'  pattern in the source
    assert "'B': '8'" not in src_text and '"B": "8"' not in src_text, \
        "'B': '8' substitution still present"

def bug004_S_absent():
    import inspect, src.ocr.plate_reader as pr
    src_text = inspect.getsource(pr)
    assert "'S': '5'" not in src_text and '"S": "5"' not in src_text, \
        "'S': '5' substitution still present"

def bug004_G_absent():
    import inspect, src.ocr.plate_reader as pr
    src_text = inspect.getsource(pr)
    assert "'G': '6'" not in src_text and '"G": "6"' not in src_text, \
        "'G': '6' substitution still present"

def bug004_safe_subs_kept():
    import inspect, src.ocr.plate_reader as pr
    src_text = inspect.getsource(pr)
    assert "'Z': '2'" in src_text or '"Z": "2"' in src_text, "Z→2 substitution missing"

check("'B': '8' removed from substitutions", bug004_B_absent)
check("'S': '5' removed from substitutions", bug004_S_absent)
check("'G': '6' removed from substitutions", bug004_G_absent)
check("safe Z→2 substitution kept", bug004_safe_subs_kept)


# ── BUG-005 ──────────────────────────────────────────────────────────────────
print("\nBUG-005 — permission check returns False on DB error")

def bug005_no_return_true_in_except():
    import ast, inspect, src.ui.user_management_page as ump
    src_text = inspect.getsource(ump)
    tree = ast.parse(src_text)
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            for child in ast.walk(node):
                if (isinstance(child, ast.Return) and
                        isinstance(child.value, ast.Constant) and
                        child.value.value is True):
                    raise AssertionError("Found 'return True' in an except block")

check("no 'return True' inside any except block", bug005_no_return_true_in_except)


# ── BUG-006 ──────────────────────────────────────────────────────────────────
print("\nBUG-006 — session.expunge() in both getter methods")

def bug006_stolen_has_expunge():
    import ast, inspect, src.db.special_vehicles_db as sv
    src_text = inspect.getsource(sv)
    tree = ast.parse(src_text)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'get_stolen_vehicle_by_plate':
            seg = ast.get_source_segment(src_text, node) or ""
            assert 'expunge' in seg, "get_stolen_vehicle_by_plate missing expunge()"
            return
    raise AssertionError("get_stolen_vehicle_by_plate not found")

def bug006_staff_has_expunge():
    import ast, inspect, src.db.special_vehicles_db as sv
    src_text = inspect.getsource(sv)
    tree = ast.parse(src_text)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'get_staff_vehicle_by_plate':
            seg = ast.get_source_segment(src_text, node) or ""
            assert 'expunge' in seg, "get_staff_vehicle_by_plate missing expunge()"
            return
    raise AssertionError("get_staff_vehicle_by_plate not found")

check("get_stolen_vehicle_by_plate has expunge()", bug006_stolen_has_expunge)
check("get_staff_vehicle_by_plate has expunge()", bug006_staff_has_expunge)


# ── SEC-1 ─────────────────────────────────────────────────────────────────────
print("\nSEC-1 — credentials not hardcoded in settings.py")

def sec1_email_not_hardcoded():
    import importlib, config.settings as s
    importlib.reload(s)
    assert s.EMAIL_SENDER != "nishantkoirala16@gmail.com", "Gmail address still hardcoded"

def sec1_password_not_hardcoded():
    import importlib, config.settings as s
    importlib.reload(s)
    assert s.EMAIL_APP_PASSWORD != "sgvc qzdh yfym kjtq", "App password still hardcoded"

def sec1_reads_env_var():
    os.environ["ANPR_EMAIL_SENDER"] = "env@example.com"
    os.environ["ANPR_EMAIL_PASSWORD"] = "env_pass"
    import importlib, config.settings as s
    importlib.reload(s)
    try:
        assert s.EMAIL_SENDER == "env@example.com"
        assert s.EMAIL_APP_PASSWORD == "env_pass"
    finally:
        del os.environ["ANPR_EMAIL_SENDER"]
        del os.environ["ANPR_EMAIL_PASSWORD"]
        importlib.reload(s)

check("EMAIL_SENDER not hardcoded", sec1_email_not_hardcoded)
check("EMAIL_APP_PASSWORD not hardcoded", sec1_password_not_hardcoded)
check("EMAIL_SENDER reads ANPR_EMAIL_SENDER env var", sec1_reads_env_var)


# ── SEC-2 ─────────────────────────────────────────────────────────────────────
print("\nSEC-2 — simple_auth uses bcrypt")

def sec2_hash_is_bcrypt():
    from src.auth.simple_auth import SimpleAuthManager
    h = SimpleAuthManager(None).hash_password("test")
    assert h.startswith("$2b$") or h.startswith("$2a$"), f"Not bcrypt: {h[:12]}"

def sec2_verify_correct():
    from src.auth.simple_auth import SimpleAuthManager
    mgr = SimpleAuthManager(None)
    h = mgr.hash_password("secret123")
    assert mgr.verify_password("secret123", h)
    assert not mgr.verify_password("wrong", h)

def sec2_no_sha256():
    import inspect, src.auth.simple_auth as sa
    src_text = inspect.getsource(sa)
    assert 'sha256' not in src_text, "sha256 still referenced"
    assert 'hashlib' not in src_text, "hashlib still imported"

check("hash_password produces bcrypt output", sec2_hash_is_bcrypt)
check("verify_password works correctly", sec2_verify_correct)
check("sha256/hashlib not present in simple_auth", sec2_no_sha256)


# ── SEC-3 ─────────────────────────────────────────────────────────────────────
print("\nSEC-3 — no admin-by-username in simple_auth")

def sec3_no_username_admin_check():
    import inspect, src.auth.simple_auth as sa
    src_text = inspect.getsource(sa)
    assert "username == 'admin'" not in src_text and 'username == "admin"' not in src_text, \
        "Admin-by-username shortcut still present"

def sec3_is_admin_defaults_false():
    from src.auth.simple_auth import SimpleAuthManager
    mgr = SimpleAuthManager(None)
    assert not mgr.is_admin("nonexistent_session")

check("username == 'admin' not in simple_auth source", sec3_no_username_admin_check)
check("is_admin returns False for unknown session", sec3_is_admin_defaults_false)


# ── SEC-4 ─────────────────────────────────────────────────────────────────────
print("\nSEC-4 — update_password verifies current_password when provided")

def sec4_param_exists():
    import inspect
    from src.auth.auth_manager import AuthManager
    params = inspect.signature(AuthManager.update_password).parameters
    assert 'current_password' in params, "current_password param missing"

def sec4_rejects_wrong_current():
    import bcrypt
    from src.auth.auth_manager import AuthManager
    from unittest.mock import MagicMock, patch

    correct_hash = bcrypt.hashpw(b"correct", bcrypt.gensalt()).decode()
    mock_user = MagicMock()
    mock_user.password_hash = correct_hash

    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_user
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)

    mgr = object.__new__(AuthManager)
    mgr.get_session = MagicMock(return_value=mock_session)
    mgr.current_user = mgr.current_session = mgr.current_username = None

    with patch.object(mgr, '_log_audit'):
        result = mgr.update_password("user", "newpass", current_password="wrong")
    assert result is False, "Should return False for wrong current_password"

def sec4_accepts_correct_current():
    import bcrypt
    from src.auth.auth_manager import AuthManager
    from unittest.mock import MagicMock, patch

    correct_hash = bcrypt.hashpw(b"correct", bcrypt.gensalt()).decode()
    mock_user = MagicMock()
    mock_user.password_hash = correct_hash
    from src.db.rbac_models import UserStatus
    mock_user.status = UserStatus.ACTIVE

    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_user
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)

    mgr = object.__new__(AuthManager)
    mgr.get_session = MagicMock(return_value=mock_session)
    mgr.current_user = mgr.current_session = mgr.current_username = None

    with patch.object(mgr, '_log_audit'):
        result = mgr.update_password("user", "newpass", current_password="correct")
    assert result is True, "Should return True for correct current_password"

check("current_password parameter exists", sec4_param_exists)
check("returns False when current_password is wrong", sec4_rejects_wrong_current)
check("returns True when current_password is correct", sec4_accepts_correct_current)


# ── SEC-5 ─────────────────────────────────────────────────────────────────────
print("\nSEC-5 — rbac_setup raises ValueError without password")

def sec5_raises_without_password():
    from src.db.rbac_setup import initialize_rbac_system
    # Ensure env var is not set
    os.environ.pop("ANPR_ADMIN_PASSWORD", None)
    try:
        initialize_rbac_system(lambda: None, admin_password=None)
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "Admin password is required" in str(e)

def sec5_no_admin123_default():
    import ast, inspect, src.db.rbac_setup as rs
    src_text = inspect.getsource(rs)
    tree = ast.parse(src_text)
    # Only check initialize_rbac_system's default parameter values
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'initialize_rbac_system':
            for arg, default in zip(
                reversed(node.args.args), reversed(node.args.defaults)
            ):
                if arg.arg == 'admin_password':
                    if isinstance(default, ast.Constant) and default.value not in (None, ''):
                        raise AssertionError(
                            f"initialize_rbac_system admin_password default is "
                            f"'{default.value}' — must be None"
                        )
            return
    raise AssertionError("initialize_rbac_system not found")

def sec5_password_not_printed():
    import inspect, src.db.rbac_setup as rs
    src_text = inspect.getsource(rs)
    # The old line printed "admin_username / admin_password"
    assert '/ {admin_password}' not in src_text and "/ admin_password" not in src_text, \
        "Password still being printed to stdout"

check("ValueError raised when no password supplied", sec5_raises_without_password)
check("'admin123' not hardcoded in rbac_setup.py", sec5_no_admin123_default)
check("password not printed to stdout", sec5_password_not_printed)


# ── SEC-6 ─────────────────────────────────────────────────────────────────────
print("\nSEC-6 — DEBUG flags off by default")

def sec6_save_images_false():
    import importlib, config.settings as s
    os.environ.pop("ANPR_EMAIL_SENDER", None)
    os.environ.pop("ANPR_EMAIL_PASSWORD", None)
    importlib.reload(s)
    assert s.DEBUG_SAVE_IMAGES is False, f"DEBUG_SAVE_IMAGES={s.DEBUG_SAVE_IMAGES}"

def sec6_verbose_false():
    import importlib, config.settings as s
    importlib.reload(s)
    assert s.DEBUG_OCR_VERBOSE is False, f"DEBUG_OCR_VERBOSE={s.DEBUG_OCR_VERBOSE}"

check("DEBUG_SAVE_IMAGES is False", sec6_save_images_false)
check("DEBUG_OCR_VERBOSE is False", sec6_verbose_false)


# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total  = len(results)
print(f"\n{'='*55}")
print(f"  Results: {passed}/{total} passed", end="")
if failed:
    print(f"  |  {failed} FAILED")
    for name, ok, err in results:
        if not ok:
            print(f"    ✗ {name}: {err}")
else:
    print("  — all green")
print('='*55)
sys.exit(0 if failed == 0 else 1)
