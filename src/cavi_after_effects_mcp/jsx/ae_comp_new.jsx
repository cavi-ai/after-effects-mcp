$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, i, item, comp, replaced = false;
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
    comp = app.project.items.addComp(a.name, a.width, a.height, 1, a.duration, a.fps);
    comp.bgColor = a.background;
    if (a.renderer) { caviRenderer(comp, a.renderer); }
    caviReport({comp: comp.name, width: comp.width, height: comp.height, duration: comp.duration,
        fps: comp.frameRate, renderer: comp.renderer, replaced: replaced, errors: []});
})();
