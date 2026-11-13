$.evalFile(new File(CAVI_LIB));

(function () {
    var scope = CAVI_ARGS.scope, report = {scope: scope, errors: []}, i, item, comp, queue, list;
    if (scope === "project") {
        report.comps = []; report.footage = []; report.folders = [];
        for (i = 1; i <= app.project.numItems; i++) {
            item = app.project.item(i);
            if (item.name === "cavi-report") { continue; }
            if (item instanceof CompItem) {
                report.comps.push({name: item.name, width: item.width, height: item.height, duration: item.duration,
                    fps: item.frameRate, layers: item.numLayers, renderer: item.renderer});
            } else if (item instanceof FolderItem) {
                report.folders.push({name: item.name, items: item.numItems});
            } else {
                report.footage.push({name: item.name, file: item.mainSource.file ? item.mainSource.file.fsName : null,
                    missing: item.footageMissing === true, width: item.width, height: item.height, duration: item.duration,
                    solid: item.mainSource instanceof SolidSource});
            }
        }
    } else if (scope === "comp") {
        comp = caviComp(CAVI_ARGS.comp);
        report.comp = comp.name; report.renderer = comp.renderer; report.layers = [];
        for (i = 1; i <= comp.numLayers; i++) {
            report.layers.push(describeLayer(comp.layer(i)));
        }
    } else {
        queue = app.project.renderQueue;
        list = [];
        for (i = 1; i <= queue.numItems; i++) {
            list.push(caviQueueItem(queue.item(i), i));
        }
        report.queue = list;
    }
    caviReport(report);
})();
