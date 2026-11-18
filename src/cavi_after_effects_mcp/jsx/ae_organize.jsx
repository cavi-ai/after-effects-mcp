$.evalFile(new File(CAVI_LIB));

// A project item by its id from ae_inspect, or by a name no other item has.
function itemByName(name, what) {
    var i, found = null;
    if (typeof name === "number") {
        found = app.project.itemByID(name);
        return found ? found : caviFail("No " + what + " with id " + name);
    }
    for (i = 1; i <= app.project.numItems; i++) {
        if (app.project.item(i).name === name && app.project.item(i).name !== "cavi-report") {
            if (found) { caviFail("More than one project item is named " + name + "; rename one first"); }
            found = app.project.item(i);
        }
    }
    if (!found) { caviFail("No " + what + " named " + name); }
    return found;
}

(function () {
    var a = CAVI_ARGS, i, made = [], moved = [], renamed = [], item, spec;
    for (i = 0; i < a.folders.length; i++) { caviFolder(a.folders[i]); made.push(a.folders[i]); }
    for (i = 0; i < a.renames.length; i++) {
        spec = a.renames[i];
        item = itemByName(spec.item, "project item");
        item.name = spec.name;
        renamed.push(spec.item + " -> " + spec.name);
    }
    for (i = 0; i < a.moves.length; i++) {
        spec = a.moves[i];
        item = itemByName(spec.item, "project item");
        item.parentFolder = caviFolder(spec.folder);
        moved.push(spec.item + " -> " + spec.folder);
    }
    caviReport({folders: made, renamed: renamed, moved: moved, errors: []});
})();
