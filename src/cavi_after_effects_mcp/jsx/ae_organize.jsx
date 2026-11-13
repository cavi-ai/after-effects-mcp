$.evalFile(new File(CAVI_LIB));

function itemByName(name, what) {
    var i, found = null;
    for (i = 1; i <= app.project.numItems; i++) {
        if (app.project.item(i).name === name && app.project.item(i).name !== "cavi-report") {
            if (found) { caviFail("More than one project item is named " + name + "; rename one first"); }
            found = app.project.item(i);
        }
    }
    if (!found) { caviFail("No " + what + " named " + name); }
    return found;
}

// A folder path "A/B" is created level by level and reused when it exists.
function folderAt(path, create) {
    var parts = path.split("/"), parent = app.project.rootFolder, i, j, child, name;
    for (i = 0; i < parts.length; i++) {
        name = parts[i];
        child = null;
        for (j = 1; j <= parent.numItems; j++) {
            if (parent.item(j) instanceof FolderItem && parent.item(j).name === name) { child = parent.item(j); }
        }
        if (!child) {
            if (!create) { caviFail("No folder " + path); }
            child = app.project.items.addFolder(name);
            child.parentFolder = parent;
        }
        parent = child;
    }
    return parent;
}

(function () {
    var a = CAVI_ARGS, i, made = [], moved = [], renamed = [], item, spec;
    for (i = 0; i < a.folders.length; i++) { folderAt(a.folders[i], true); made.push(a.folders[i]); }
    for (i = 0; i < a.renames.length; i++) {
        spec = a.renames[i];
        item = itemByName(spec.item, "project item");
        item.name = spec.name;
        renamed.push(spec.item + " -> " + spec.name);
    }
    for (i = 0; i < a.moves.length; i++) {
        spec = a.moves[i];
        item = itemByName(spec.item, "project item");
        item.parentFolder = folderAt(spec.folder, true);
        moved.push(spec.item + " -> " + spec.folder);
    }
    caviReport({folders: made, renamed: renamed, moved: moved, errors: []});
})();
