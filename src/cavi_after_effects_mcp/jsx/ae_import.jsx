$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, folder = a.folder ? caviFolder(a.folder) : null, items = [], i, j, file, options, item, list = [], source,
        alpha = {IGNORE: AlphaMode.IGNORE, STRAIGHT: AlphaMode.STRAIGHT, PREMULTIPLIED: AlphaMode.PREMULTIPLIED},
        kinds = {COMP: ImportAsType.COMP, COMP_CROPPED: ImportAsType.COMP_CROPPED_LAYERS, FOOTAGE: ImportAsType.FOOTAGE};
    for (i = 0; i < a.files.length; i++) {
        file = new File(a.files[i]);
        if (!file.exists) { caviFail("No file at " + a.files[i]); }
        options = new ImportOptions(file);
        if (a.sequence) {
            options.sequence = true;
            options.forceAlphabetical = true;
        }
        if (a.as !== "footage") { options.importAs = caviEnum(kinds, a.as, "import type"); }
        items.push(app.project.importFile(options));
    }
    for (j = 0; j < items.length; j++) {
        item = items[j];
        if (folder) { item.parentFolder = folder; }
        if (item instanceof FolderItem) {
            // An imported .aep arrives as one folder holding its items.
            list.push({name: item.name, type: "project", folder: item.parentFolder.name, comps: caviFolderComps(item, [])});
            continue;
        }
        source = item instanceof FootageItem ? item.mainSource : null;
        if (source && a.alpha !== null) { source.alphaMode = caviEnum(alpha, a.alpha, "alpha mode"); }
        if (source && a.conform_fps !== null) { source.conformFrameRate = a.conform_fps; }
        if (source && a.loop !== null) { source.loop = a.loop; }
        list.push({name: item.name, type: item instanceof CompItem ? "comp" : "footage", width: item.width,
            height: item.height, duration: item.duration, frame_rate: item.frameRate,
            alpha: source && source.hasAlpha ? String(source.alphaMode) : null,
            conform_fps: source ? source.conformFrameRate : null, loop: source ? source.loop : null,
            folder: item.parentFolder.name, layers: item instanceof CompItem ? item.numLayers : null});
    }
    caviReport({items: list, errors: []});
})();

function caviFolderComps(folder, out) {
    var i, item;
    for (i = 1; i <= folder.numItems; i++) {
        item = folder.item(i);
        if (item instanceof CompItem) { out.push(item.name); } else if (item instanceof FolderItem) { caviFolderComps(item, out); }
    }
    return out;
}
