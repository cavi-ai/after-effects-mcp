$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, i, item, comp, replaced = false, renderers = [];
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
    if (a.renderer) {
        for (i = 0; i < comp.renderers.length; i++) {
            renderers.push(comp.renderers[i]);
        }
        if (("," + renderers.join(",") + ",").indexOf("," + a.renderer + ",") < 0) {
            caviFail("Renderer " + a.renderer + " is not one of " + renderers.join(", "));
        }
        comp.renderer = a.renderer;
    }
    caviReport({comp: comp.name, width: comp.width, height: comp.height, duration: comp.duration,
        fps: comp.frameRate, renderer: comp.renderer, replaced: replaced, errors: []});
})();
