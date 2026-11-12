// Runs the script at CAVI_SCRIPT with CAVI_ARGS. Scripts in -noui cannot write files, so the report
// is the comment of the project folder "cavi-report", saved with the project at CAVI_PROJECT.
// A script calls caviReport(object) to set its report; otherwise the report is its last value.
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
        return '"' + value.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n")
            .replace(/\r/g, "\\r").replace(/\t/g, "\\t") + '"';
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
    var folder = null, i, item;
    for (i = 1; i <= app.project.numItems; i++) {
        item = app.project.item(i);
        if (item instanceof FolderItem && item.name === "cavi-report") {
            folder = item;
        }
    }
    if (!folder) {
        folder = app.project.items.addFolder("cavi-report");
    }
    folder.comment = "CAVI_REPORT" + caviStringify(report) + "CAVI_END";
    app.project.save(new File(CAVI_PROJECT));
    CAVI_REPORTED = true;
}

(function () {
    var file = new File(CAVI_SCRIPT), source, value;
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
        value = $.evalFile(file);
    } catch (failure) {
        caviReport({errors: [where(failure, 0)]});
        return;
    }
    if (!CAVI_REPORTED) {
        caviReport({value: value === undefined ? null : String(value), errors: []});
    }
})();
