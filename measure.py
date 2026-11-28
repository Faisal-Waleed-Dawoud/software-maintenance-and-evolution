"""Measures the quality numbers used in Section 7 of the report.

Install once:   pip install radon
Run:            python measure.py main.py database.py ...  [--data-layer database.py]
List every .py file of the project (leave out test files and the one-time migration script).
--data-layer: the file(s) that are allowed to talk to the database (leave it out for the original code).
"""
import argparse
import ast
from radon.complexity import cc_visit
from radon.raw import analyze

DRIVERS = ("sqlite3", "psycopg2", "psycopg", "mysql", "pymysql", "sqlalchemy", "pymongo")
DB_CALLS = ("cursor", "execute", "executemany", "executescript", "commit", "close",
            "connect", "fetchone", "fetchall")

parser = argparse.ArgumentParser()
parser.add_argument("files", nargs="+")
parser.add_argument("--data-layer", nargs="*", default=[])
args = parser.parse_args()

total = dict(loc=0, sloc=0, funcs=0, classes=0, driver_files=0, db_funcs_outside=0,
             execute_outside=0, execute_all=0)
all_cc = []

for path in args.files:
    code = open(path, encoding="utf-8").read()
    tree = ast.parse(code)
    raw = analyze(code)
    blocks = cc_visit(code)
    funcs = [b for b in blocks if b.__class__.__name__ == "Function"]
    classes = [b for b in blocks if b.__class__.__name__ == "Class"]
    inside = path in args.data_layer

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    uses_driver = any(d in imports for d in DRIVERS)

    def db_calls(node):
        names = [n.func.attr for n in ast.walk(node)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        return [x for x in names if x in DB_CALLS]

    db_funcs = 0
    executes = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            calls = db_calls(node)
            if calls:
                db_funcs += 1
                print("   uses DB:", path + ":" + node.name)
    executes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Attribute) and n.func.attr == "execute")

    print("\n== %s %s" % (path, "(data layer)" if inside else ""))
    print("   LOC (all lines): %d   SLOC (no blank/comment lines): %d" % (raw.loc, raw.sloc))
    print("   functions: %d   classes: %d" % (len(funcs), len(classes)))
    for f in funcs:
        print("   CC %2d  %s" % (f.complexity, f.fullname))
        all_cc.append((path, f.fullname, f.complexity))
    print("   imports a database driver: %s   execute() calls: %d" % (uses_driver, executes))

    total["loc"] += raw.loc
    total["sloc"] += raw.sloc
    total["funcs"] += len(funcs)
    total["classes"] += len(classes)
    total["driver_files"] += 1 if uses_driver else 0
    total["execute_all"] += executes
    if not inside:
        total["db_funcs_outside"] += db_funcs
        total["execute_outside"] += executes

print("\n================ TOTALS ================")
print("7.1 LOC (all lines):                          ", total["loc"])
print("7.1 SLOC (no blank/comment lines):            ", total["sloc"])
print("7.2 Number of functions:                      ", total["funcs"])
print("7.3 Number of classes:                        ", total["classes"])
if all_cc:
    values = [c for _, _, c in all_cc]
    print("7.4 Cyclomatic complexity: average %.1f, highest %d (%s)" % (
        sum(values) / len(values), max(values), max(all_cc, key=lambda x: x[2])[1]))
print("7.6 Files importing a database driver:        ", total["driver_files"])
print("7.6 Functions using the DB outside data layer:", total["db_funcs_outside"])
print("7.6 execute() calls outside the data layer:   ", total["execute_outside"], "(all files:", total["execute_all"], ")")
