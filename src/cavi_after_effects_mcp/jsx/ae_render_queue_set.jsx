$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, queue = app.project.renderQueue, i, spec, item, module, added = [], list = [];
    if (a.clear) {
        for (i = queue.numItems; i >= 1; i--) {
            queue.item(i).remove();
        }
    }
    for (i = 0; i < a.add.length; i++) {
        spec = a.add[i];
        item = queue.items.add(caviComp(spec.comp));
        item.applyTemplate(spec.render_settings);
        module = item.outputModule(1);
        module.applyTemplate(spec.output_module);
        module.file = new File(spec.file);
        if (spec.locked) {
            item.render = false;
            item.comp.label = 0;
        }
        added.push(queue.numItems);
    }
    for (i = 0; i < a.update.length; i++) {
        spec = a.update[i];
        if (spec.index < 1 || spec.index > queue.numItems) {
            caviFail("The render queue has no item " + spec.index);
        }
        item = queue.item(spec.index);
        if (spec.locked) {
            item.render = false;
            item.comp.label = 0;
        }
        if (spec.render !== null) { item.render = spec.render; }
        if (spec.label !== null) { item.comp.label = spec.label; }
    }
    for (i = 1; i <= queue.numItems; i++) {
        list.push(caviQueueItem(queue.item(i), i));
    }
    caviReport({added: added, queue: list, errors: []});
})();
