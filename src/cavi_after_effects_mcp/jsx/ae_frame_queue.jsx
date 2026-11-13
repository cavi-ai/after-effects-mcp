$.evalFile(new File(CAVI_LIB));

// add: one single-frame queue entry per time, other entries switched off. remove: drops those entries and
// switches the previously enabled ones back on.
(function () {
    var a = CAVI_ARGS, queue = app.project.renderQueue, i, item, module, comp, enabled = [], added = 0;
    if (a.action === "add") {
        comp = caviComp(a.comp);
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
        for (i = 0; i < a.count; i++) {
            queue.item(queue.numItems).remove();
        }
        for (i = 0; i < a.enabled.length; i++) { queue.item(a.enabled[i]).render = true; }
    }
    caviReport({action: a.action, added: added, enabled: enabled, queue_items: queue.numItems, errors: []});
})();
