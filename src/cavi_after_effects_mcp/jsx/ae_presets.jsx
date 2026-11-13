$.evalFile(new File(CAVI_LIB));

(function () {
    var queue = app.project.renderQueue, item, temp = null, i, settings = [], modules = [], fresh = false, module;
    if (queue.numItems === 0) {
        temp = app.project.items.addComp("cavi-presets", 4, 4, 1, 1, 1);
        item = queue.items.add(temp);
        fresh = true;
    } else {
        item = queue.item(1);
    }
    module = item.outputModule(1);
    for (i = 0; i < item.templates.length; i++) { settings.push(item.templates[i]); }
    for (i = 0; i < module.templates.length; i++) { modules.push(module.templates[i]); }
    if (fresh) {
        item.remove();
        temp.remove();
    }
    caviReport({render_settings: settings, output_modules: modules, errors: []});
})();
