$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, i, item, comp, replaced = false, source = null, layer = null, width = a.width, height = a.height,
        duration = a.duration, fps = a.fps, aspect = 1;
    for (i = app.project.numItems; i >= 1; i--) {
        item = app.project.item(i);
        if (item instanceof CompItem && item.name === a.name) {
            if (!a.replace) {
                caviFail("Comp " + a.name + " exists; pass replace to rebuild it");
            }
            item.remove();
            replaced = true;
        }
    }
    if (a.footage !== null) {
        source = caviFootage(a.footage);
        if (!source.hasVideo && (width === null || height === null)) {
            caviFail("Footage " + source.name + " has no picture; give width and height");
        }
        if (width === null) { width = source.width; }
        if (height === null) { height = source.height; }
        if (duration === null) {
            if (source.mainSource.isStill) { caviFail("Footage " + source.name + " is a still; give duration"); }
            duration = source.duration;
        }
        if (fps === null) { fps = source.frameRate > 0 ? source.frameRate : 30; }
        if (source.hasVideo) { aspect = source.pixelAspect; }
    }
    if (fps === null) { fps = 30; }
    comp = app.project.items.addComp(a.name, width, height, aspect, duration, fps);
    comp.bgColor = a.background;
    if (a.renderer) { caviRenderer(comp, a.renderer); }
    if (source !== null) {
        layer = comp.layers.add(source);
        layer.startTime = 0;
        layer = {index: layer.index, name: layer.name, in_point: layer.inPoint, out_point: layer.outPoint};
    }
    caviReport({comp: comp.name, width: comp.width, height: comp.height, pixel_aspect: comp.pixelAspect,
        duration: comp.duration, fps: comp.frameRate, renderer: comp.renderer, replaced: replaced,
        footage: source === null ? null : {id: source.id, name: source.name}, layer: layer, errors: []});
})();
