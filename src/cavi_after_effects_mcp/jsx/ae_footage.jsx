$.evalFile(new File(CAVI_LIB));

// The same alpha table as ae_import.jsx. caviNameOf reports the lowercase word.
function caviAlphaModes() {
    return {IGNORE: AlphaMode.IGNORE, STRAIGHT: AlphaMode.STRAIGHT, PREMULTIPLIED: AlphaMode.PREMULTIPLIED};
}

function caviFootageItem(ref) {
    var i, item, found = [], ids = [];
    if (typeof ref === "number") {
        item = app.project.itemByID(ref);
        if (!item) { caviFail("No footage item with id " + ref); }
        if (!(item instanceof FootageItem)) { caviFail("Item " + ref + " is not footage"); }
        return item;
    }
    for (i = 1; i <= app.project.numItems; i++) {
        item = app.project.item(i);
        if (item instanceof FootageItem && item.name === ref) {
            found.push(item);
            ids.push(item.id);
        }
    }
    if (found.length > 1) {
        caviFail(found.length + " footage items are named " + ref + " (item ids " + ids.join(", ") + "); pass the id");
    }
    return found.length ? found[0] : caviFail("No footage item named " + ref);
}

function caviFootageState(item) {
    var source = item.mainSource, fileSource = source instanceof FileSource, proxy = item.proxySource;
    return {
        id: item.id,
        name: item.name,
        file: fileSource && source.file ? source.file.fsName : null,
        missing: item.footageMissing === true,
        alpha: fileSource && source.hasAlpha ? caviNameOf(caviAlphaModes(), source.alphaMode) : null,
        invert_alpha: fileSource ? source.invertAlpha === true : false,
        conform_fps: fileSource ? source.conformFrameRate : null,
        native_fps: fileSource ? source.nativeFrameRate : null,
        pixel_aspect: item.pixelAspect,
        proxy: proxy && proxy.file ? proxy.file.fsName : null,
        use_proxy: item.useProxy === true
    };
}

function caviFileSource(item) {
    if (!(item.mainSource instanceof FileSource)) {
        caviFail("Footage " + item.name + " has no file source");
    }
    return item.mainSource;
}

function caviWalkFiles(folder, out, seen) {
    var entries, i, path;
    path = folder.fsName;
    if (seen[path]) { return; }
    seen[path] = true;
    entries = folder.getFiles();
    if (!entries) { return; }
    for (i = 0; i < entries.length; i++) {
        if (entries[i] instanceof Folder) {
            caviWalkFiles(entries[i], out, seen);
        } else if (entries[i] instanceof File) {
            out.push(entries[i]);
        }
    }
}

function caviRelinkItem(item, files) {
    var name, i, matches = [], paths = [], state;
    state = caviFootageState(item);
    state.relinked = false;
    state.ambiguous = [];
    if (item.footageMissing !== true) { return state; }
    if (!(item.mainSource instanceof FileSource) || !item.mainSource.file) { return state; }
    name = item.mainSource.file.name;
    for (i = 0; i < files.length; i++) {
        if (files[i].name === name) { matches.push(files[i]); }
    }
    if (matches.length === 1) {
        item.replace(matches[0]);
        state = caviFootageState(item);
        state.relinked = true;
        state.ambiguous = [];
        return state;
    }
    if (matches.length > 1) {
        for (i = 0; i < matches.length; i++) { paths.push(matches[i].fsName); }
        state.ambiguous = paths;
    }
    return state;
}

(function () {
    var a = CAVI_ARGS, item, list = [], i, file, folder, files, targets = [];
    if (a.action === "relink") {
        folder = new Folder(a.folder);
        if (!folder.exists) { caviFail("No folder at " + a.folder); }
        files = [];
        caviWalkFiles(folder, files, {});
        if (a.item === null || a.item === undefined) {
            for (i = 1; i <= app.project.numItems; i++) {
                item = app.project.item(i);
                if (item instanceof FootageItem && item.name !== "cavi-report" && item.footageMissing === true) {
                    targets.push(item);
                }
            }
        } else {
            targets.push(caviFootageItem(a.item));
        }
        for (i = 0; i < targets.length; i++) { list.push(caviRelinkItem(targets[i], files)); }
    } else {
        item = caviFootageItem(a.item);
        if (a.action === "interpret") {
            if (a.conform_fps !== null && caviFileSource(item).isStill) {
                caviFail("Footage " + item.name + " is a still (isStill); conform_fps is refused");
            }
            if (a.alpha !== null) {
                caviFileSource(item).alphaMode = caviEnum(caviAlphaModes(), a.alpha, "alpha mode");
            }
            if (a.invert_alpha !== null) { caviFileSource(item).invertAlpha = a.invert_alpha; }
            if (a.conform_fps !== null) { caviFileSource(item).conformFrameRate = a.conform_fps; }
            if (a.pixel_aspect !== null) { item.pixelAspect = a.pixel_aspect; }
        } else if (a.action === "proxy") {
            if (a.file !== null) {
                file = new File(a.file);
                if (!file.exists) { caviFail("No file at " + a.file); }
                item.setProxy(file);
            }
            if (a.clear) { item.setProxyToNone(); }
            if (a.use_proxy !== null) { item.useProxy = a.use_proxy; }
        }
        list.push(caviFootageState(item));
    }
    caviReport({action: a.action, items: list, errors: []});
})();
