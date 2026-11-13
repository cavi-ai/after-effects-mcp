$.evalFile(new File(CAVI_LIB));

function counts() {
    var i, item, comps = 0, footage = 0;
    for (i = 1; i <= app.project.numItems; i++) {
        item = app.project.item(i);
        if (item instanceof CompItem) { comps++; } else if (item instanceof FootageItem) { footage++; }
    }
    return {items: app.project.numItems, comps: comps, footage: footage};
}

(function () {
    var a = CAVI_ARGS, open = app.project.file ? app.project.file.fsName : null, target = new File(a.path || ""), report, keep = [], removed = null, i;
    // Reports of a refused call go to the fallback project so a project on disk is never overwritten.
    CAVI_PROJECT = a.fallback;
    if (a.action === "open") {
        if (!target.exists) { caviFail("No project at " + a.path); }
        if (app.project.dirty && !a.discard) {
            caviFail("The open project " + (open || "(untitled)") + " has unsaved changes; save it or set discard");
        }
        app.open(target);
        CAVI_PROJECT = a.path;
    } else if (a.action === "reduce" || a.action === "remove_unused" || a.action === "consolidate") {
        // These rewrite the open project; a path saves the result elsewhere and leaves the file alone.
        if (a.action === "reduce") {
            for (i = 0; i < a.comps.length; i++) { keep.push(caviComp(a.comps[i])); }
            removed = app.project.reduceProject(keep);
        } else if (a.action === "remove_unused") {
            removed = app.project.removeUnusedFootage();
        } else {
            removed = app.project.consolidateFootage();
        }
        CAVI_PROJECT = a.path || open || a.fallback;
    } else if (a.action === "save_as") {
        if (target.exists && !a.overwrite) { caviFail(a.path + " exists; set overwrite to replace it"); }
        CAVI_PROJECT = a.path;
    } else {
        if (a.action === "save" && !open) { caviFail("The open project has no file; use save_as"); }
        if (open && a.path !== null && target.fsName !== open) {
            CAVI_PROJECT = open;
            caviFail("The open project is " + open + ", not " + a.path);
        }
        CAVI_PROJECT = open || a.fallback;
    }
    report = counts();
    report.action = a.action;
    report.removed = removed;
    report.previous = open;
    report.path = a.action === "info" ? open : CAVI_PROJECT;
    report.errors = [];
    caviReport(report);
})();
