$.evalFile(new File(CAVI_LIB));

// Runs each step's packaged script in turn with its arguments. A step's report is kept instead of saved, so the
// project is saved once after the last step; a step that throws or reports errors rolls back every step.
(function () {
    var a = CAVI_ARGS, folder = new File(CAVI_LIB).parent.fsName, save = caviReport, reports = [], current, i, step, label;
    caviReport = function (report) { current = report; };
    try {
        for (i = 0; i < a.steps.length; i++) {
            step = a.steps[i];
            label = "Step " + (i + 1) + " (" + step.name + ")";
            current = null;
            CAVI_ARGS = step.args;
            try {
                $.evalFile(new File(folder + "/" + step.name + ".jsx"));
            } catch (failure) {
                caviFail(label + ": " + (failure.message || String(failure)));
            }
            if (current === null) { caviFail(label + " reported nothing"); }
            if (current.errors && current.errors.length) { caviFail(label + ": " + current.errors.join("; ")); }
            delete current.errors;
            reports.push(current);
        }
    } finally {
        caviReport = save;
        CAVI_ARGS = a;
    }
    caviReport({steps: reports, errors: []});
})();
