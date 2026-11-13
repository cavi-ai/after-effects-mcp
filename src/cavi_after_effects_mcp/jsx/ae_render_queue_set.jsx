$.evalFile(new File(CAVI_LIB));

function span(item, kind) {
    var comp = item.comp;
    if (kind === null) { return; }
    if (kind === "comp") {
        item.timeSpanStart = 0;
        item.timeSpanDuration = comp.duration;
    } else if (kind === "work_area") {
        item.timeSpanStart = comp.workAreaStart;
        item.timeSpanDuration = comp.workAreaDuration;
    } else {
        item.timeSpanStart = kind.start;
        item.timeSpanDuration = kind.duration;
    }
}

// Only the settings scripts can set; Format, Channels, Depth and Color are read-only and come from the template.
function moduleSettings(module, s) {
    var o = {}, rates = {on: "On", off: "Off", auto: "Auto"}, quality = {low: "Low", high: "High"};
    if (s === null) { return; }
    if (s.resize !== null) { o["Resize"] = true; o["Resize to"] = s.resize; }
    if (s.resize_quality !== null) { o["Resize Quality"] = quality[s.resize_quality]; }
    if (s.crop !== null) {
        o["Crop"] = true;
        o["Crop Top"] = s.crop[0]; o["Crop Left"] = s.crop[1]; o["Crop Bottom"] = s.crop[2]; o["Crop Right"] = s.crop[3];
    }
    if (s.audio !== null) { o["Output Audio"] = rates[s.audio]; }
    if (s.audio_sample_rate !== null) { o["Audio Sample Rate"] = s.audio_sample_rate; }
    if (s.audio_channels !== null) { o["Audio Channels"] = s.audio_channels === "mono" ? "Mono" : "Stereo"; }
    if (s.audio_bit_depth !== null) { o["Audio Bit Depth"] = s.audio_bit_depth + " Bit"; }
    module.setSettings(o);
}

// Render settings keys setSettings accepts; a frame rate is the "Use this frame rate" number plus the mode key.
function renderSettings(item, s) {
    var o = {}, labels = {full: "Full", half: "Half", third: "Third", quarter: "Quarter", draft: "Draft", best: "Best",
        wireframe: "Wireframe", none: "Use No Proxies", comp: "Use Comp Proxies Only", all: "Use All Proxies",
        on: "All On", off: "All Off", current: "Current Settings", checked: "On for Checked Layers",
        off_all: "Off for All Layers"};
    if (s === null) { return; }
    if (s.quality !== null) { o["Quality"] = labels[s.quality]; }
    if (s.resolution !== null) { o["Resolution"] = labels[s.resolution]; }
    if (s.proxy_use !== null) { o["Proxy Use"] = labels[s.proxy_use]; }
    if (s.effects !== null) { o["Effects"] = labels[s.effects]; }
    if (s.motion_blur !== null) { o["Motion Blur"] = labels[s.motion_blur]; }
    if (s.frame_blending !== null) { o["Frame Blending"] = labels[s.frame_blending]; }
    if (s.frame_rate !== null) { o["Use this frame rate"] = s.frame_rate; }
    item.setSettings(o);
}

(function () {
    var a = CAVI_ARGS, queue = app.project.renderQueue, i, spec, item, module, added = [], list = [], j;
    function has(list, name) {
        var k;
        for (k = 0; k < list.length; k++) {
            if (list[k] === name) { return true; }
        }
        return false;
    }
    if (a.clear) {
        for (i = queue.numItems; i >= 1; i--) {
            item = queue.item(i);
            for (j = 0; j < a.add.length; j++) {
                if (item.comp.name === a.add[j].comp) { item.remove(); break; }
            }
        }
    }
    for (i = 0; i < a.add.length; i++) {
        spec = a.add[i];
        item = queue.items.add(caviComp(spec.comp));
        module = item.outputModule(1);
        if (!has(item.templates, spec.render_settings) || !has(module.templates, spec.output_module)) {
            item.remove();
            caviFail("Unknown template; use the names ae_presets lists: " + spec.render_settings + " / " + spec.output_module);
        }
        item.applyTemplate(spec.render_settings);
        module.applyTemplate(spec.output_module);
        module.file = new File(spec.file);
        span(item, spec.time_span);
        moduleSettings(module, spec.output);
        renderSettings(item, spec.settings);
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
        renderSettings(item, spec.settings);
        if (spec.duplicate) { item.duplicate(); }
        if (spec.remove) { item.remove(); }
    }
    for (i = 1; i <= queue.numItems; i++) {
        list.push(caviQueueItem(queue.item(i), i));
    }
    caviReport({added: added, queue: list, errors: []});
})();
