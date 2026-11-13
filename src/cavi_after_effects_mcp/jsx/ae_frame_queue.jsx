$.evalFile(new File(CAVI_LIB));

// add: with background, a solid of the comp's background color at the bottom; one single-frame queue entry per time, other entries switched off. remove: drops those entries and
// switches the previously enabled ones back on and drops the background solid.
(function () {
    var a = CAVI_ARGS, queue = app.project.renderQueue, i, item, module, comp, enabled = [], added = 0, backdrop;
    if (a.action === "add") {
        comp = caviComp(a.comp);
        if (a.background) {
            backdrop = comp.layers.addSolid(comp.bgColor, "cavi-frame-bg", comp.width, comp.height, comp.pixelAspect, comp.duration);
            backdrop.moveToEnd();
        }
        for (i = 1; i <= queue.numItems; i++) {
            if (queue.item(i).render) { enabled.push(i); queue.item(i).render = false; }
        }
        for (i = 0; i < a.frames.length; i++) {
            item = queue.items.add(comp);
            item.applyTemplate("Best Settings");
            item.timeSpanStart = a.frames[i].time;
            item.timeSpanDuration = comp.frameDuration;
            module = item.outputModule(1);
            module.applyTemplate(a.output_module);
            module.file = new File(a.frames[i].file);
            added++;
        }
    } else {
        comp = caviComp(a.comp);
        for (i = comp.numLayers; i >= 1; i--) {
            if (comp.layer(i).name === "cavi-frame-bg") {
                backdrop = comp.layer(i).source;
                comp.layer(i).remove();
                if (backdrop.usedIn.length === 0) { backdrop.remove(); }
            }
        }
        for (i = 0; i < a.count; i++) {
            queue.item(queue.numItems).remove();
        }
        for (i = 0; i < a.enabled.length; i++) { queue.item(a.enabled[i]).render = true; }
    }
    caviReport({action: a.action, added: added, enabled: enabled, queue_items: queue.numItems, errors: []});
})();
