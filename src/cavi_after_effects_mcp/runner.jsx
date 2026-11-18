// Runs the script at CAVI_SCRIPT with CAVI_ARGS and writes its report as JSON to CAVI_REPORT_FILE.
// A script calls caviReport(object) to set its report; otherwise the report is its last value.
// The project is saved to CAVI_PROJECT only when it changed or is not yet that file, so a read leaves it alone.
var CAVI_REPORTED = false;

function caviStringify(value) {
    var parts = [], i, key;
    if (value === null || value === undefined) {
        return "null";
    }
    if (typeof value === "number") {
        return isFinite(value) ? String(value) : "null";
    }
    if (typeof value === "boolean") {
        return String(value);
    }
    if (typeof value === "string") {
        // Every control character is escaped: the folder comment that holds the report drops them raw.
        return '"' + value.replace(/[\\"\x00-\x1f]/g, function (c) {
            var code = c.charCodeAt(0);
            if (c === "\\" || c === '"') {
                return "\\" + c;
            }
            if (code === 10) {
                return "\\n";
            }
            if (code === 13) {
                return "\\r";
            }
            if (code === 9) {
                return "\\t";
            }
            return "\\u" + ("000" + code.toString(16)).slice(-4);
        }) + '"';
    }
    if (value instanceof Array) {
        for (i = 0; i < value.length; i++) {
            parts.push(caviStringify(value[i]));
        }
        return "[" + parts.join(",") + "]";
    }
    for (key in value) {
        if (value.hasOwnProperty(key)) {
            parts.push(caviStringify(String(key)) + ":" + caviStringify(value[key]));
        }
    }
    return "{" + parts.join(",") + "}";
}

function caviReport(report) {
    var target = CAVI_PROJECT ? new File(CAVI_PROJECT) : null, open = app.project.file, out = new File(CAVI_REPORT_FILE);
    if (target && (app.project.dirty || !open || open.fsName !== target.fsName)) {
        app.project.save(target);
    }
    out.encoding = "UTF-8";
    if (!out.open("w") || !out.write(caviStringify(report)) || !out.close()) {
        throw new Error("Cannot write the report to " + CAVI_REPORT_FILE + ": " + out.error);
    }
    CAVI_REPORTED = true;
}

// A failed script leaves no partial edits: the open project is reloaded from disk when it is the target and changed.
// Returns "restored" when the open project is the target as saved before the script, "failed" when the reload
// failed, so that an empty project is never saved over the target, and "kept" otherwise.
function caviRollback() {
    var target = CAVI_PROJECT ? new File(CAVI_PROJECT) : null, open = app.project.file;
    if (CAVI_REPORTED || !target || !target.exists || !open || open.fsName !== target.fsName) { return "kept"; }
    if (!app.project.dirty) { return "restored"; }
    try {
        app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        app.open(target);
    } catch (reload) {
        return "failed";
    }
    return "restored";
}

(function () {
    var file = new File(CAVI_SCRIPT), source, value, quiet = false, rollback;
    function where(error, offset) {
        return String(error) + (error.line ? " (line " + (error.line - offset) + ")" : "");
    }
    file.encoding = "UTF-8";
    if (!file.open("r")) {
        caviReport({errors: ["Cannot read " + CAVI_SCRIPT]});
        return;
    }
    source = file.read();
    file.close();
    // $.evalFile of a file with a syntax error aborts DoScript before any catch runs, so compile first.
    try {
        new Function(source.replace(/^[ \t]*#.*$/gm, ""));
    } catch (syntax) {
        // new Function counts its own header as line 1.
        caviReport({errors: ["Syntax error in " + file.name + ": " + where(syntax, 1)]});
        return;
    }
    try {
        app.beginSuppressDialogs();
        quiet = true;
    } catch (unsupported) {
        quiet = false;
    }
    try {
        value = $.evalFile(file);
    } catch (failure) {
        if (quiet) { app.endSuppressDialogs(false); }
        rollback = caviRollback();
        if (rollback !== "failed") { caviReport({errors: [where(failure, 0)], restored: rollback === "restored"}); }
        return;
    }
    if (quiet) { app.endSuppressDialogs(false); }
    if (!CAVI_REPORTED) {
        caviReport({value: value === undefined ? null : String(value), errors: []});
    }
})();
