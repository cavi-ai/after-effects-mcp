$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), file = new File(a.path);
    if (!file.exists) { caviFail("No preset at " + a.path); }
    comp.time = a.time;
    layer.selected = true;
    layer.applyPreset(file);
    caviReport({comp: comp.name, layer: layer.name, preset: file.name, time: a.time, errors: []});
})();
