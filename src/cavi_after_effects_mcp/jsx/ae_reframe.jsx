$.evalFile(new File(CAVI_LIB));

function aspectSize(aspect) {
    if (aspect === "1920x1080") { return [1920, 1080]; }
    if (aspect === "1080x1920") { return [1080, 1920]; }
    if (aspect === "1080x1080") { return [1080, 1080]; }
    if (aspect === "1080x1350") { return [1080, 1350]; }
    caviFail("Unknown aspect " + aspect);
}

function findComp(name) {
    var i, item;
    for (i = 1; i <= app.project.numItems; i++) {
        item = app.project.item(i);
        if (item instanceof CompItem && item.name === name) { return item; }
    }
    return null;
}

function leaveReason(layer) {
    if (layer instanceof CameraLayer) { return "camera"; }
    if (layer instanceof LightLayer) { return "light"; }
    if (layer.threeDLayer === true) { return "3d"; }
    if (layer.locked) { return "locked"; }
    return null;
}

// A moved parent carries every descendant. Those layers already keep the new offset.
function carried(layer) {
    var guard = 0, parent = layer.parent;
    while (parent && guard < 100) {
        if (leaveReason(parent) === null) { return true; }
        parent = parent.parent;
        guard++;
    }
    return false;
}

// Corners of sourceRectAtTime in comp space, so scale, rotation and parents are part of the box.
function pointInComp(layer, x, y) {
    return layer.sourcePointToComp([x, y]);
}

function compVecToLayer(layer, dx, dy) {
    var origin = layer.compPointToSource([0, 0]), tip = layer.compPointToSource([dx, dy]);
    return [tip[0] - origin[0], tip[1] - origin[1]];
}

function compBounds(layer, time) {
    var rect = layer.sourceRectAtTime(time, false), corners, i, point, box;
    corners = [[rect.left, rect.top], [rect.left + rect.width, rect.top],
        [rect.left, rect.top + rect.height], [rect.left + rect.width, rect.top + rect.height]];
    point = pointInComp(layer, corners[0][0], corners[0][1]);
    box = {left: point[0], top: point[1], right: point[0], bottom: point[1]};
    for (i = 1; i < corners.length; i++) {
        point = pointInComp(layer, corners[i][0], corners[i][1]);
        if (point[0] < box.left) { box.left = point[0]; }
        if (point[0] > box.right) { box.right = point[0]; }
        if (point[1] < box.top) { box.top = point[1]; }
        if (point[1] > box.bottom) { box.bottom = point[1]; }
    }
    return box;
}

function boxCenter(box) {
    return [(box.left + box.right) / 2, (box.top + box.bottom) / 2];
}

function boundsOffset(layer, time, width, height) {
    var center = boxCenter(compBounds(layer, time));
    return [center[0] - width / 2, center[1] - height / 2];
}

// Restore the offset from the new center. When the resize leaves positions put, this is
// ((newWidth - oldWidth) / 2, (newHeight - oldHeight) / 2).
function centerShift(layer, time, width, height, offset) {
    var center = boxCenter(compBounds(layer, time));
    return [width / 2 + offset[0] - center[0], height / 2 + offset[1] - center[1]];
}

function addPositionSpace(layer, dx, dy) {
    var pos = layer.property("ADBE Transform Group").property("ADBE Position"), i;
    function shifted(value) {
        var out = [value[0] + dx, value[1] + dy];
        if (value.length > 2) { out.push(value[2]); }
        return out;
    }
    if (pos.numKeys === 0) {
        pos.setValue(shifted(pos.value));
    } else {
        for (i = 1; i <= pos.numKeys; i++) { pos.setValueAtKey(i, shifted(pos.keyValue(i))); }
    }
    return [dx, dy];
}

// dx, dy are comp space. Position is parent space when the layer has a parent.
function moveBy(layer, dx, dy) {
    var space;
    if (dx === 0 && dy === 0) { return [0, 0]; }
    space = layer.parent ? compVecToLayer(layer.parent, dx, dy) : [dx, dy];
    return addPositionSpace(layer, space[0], space[1]);
}

function whole(value) {
    var rounded = Math.round(value);
    if (Math.abs(rounded - value) > 0.001) { caviFail("Comp size is not a whole number of pixels: " + value); }
    return rounded;
}

function reframeOne(comp, aspect, time, left) {
    var size = aspectSize(aspect), copy = comp.duplicate(), saved, oldW, oldH, duration, fps, par, renderer;
    var plan = [], shifts = [], i, layer, reason, shift, moved = 0;
    copy.name = comp.name + " " + aspect;
    duration = copy.duration;
    fps = copy.frameRate;
    par = copy.pixelAspect;
    renderer = copy.renderer;
    oldW = copy.width;
    oldH = copy.height;
    saved = copy.time;
    copy.time = time;
    for (i = 1; i <= copy.numLayers; i++) {
        layer = copy.layer(i);
        reason = leaveReason(layer);
        if (reason) {
            left.push({comp: copy.name, layer: layer.name, index: layer.index, reason: reason});
        } else if (!carried(layer)) {
            plan.push({layer: layer, offset: boundsOffset(layer, time, oldW, oldH)});
        }
    }
    copy.width = size[0];
    copy.height = size[1];
    if (copy.duration !== duration) { copy.duration = duration; }
    if (copy.frameRate !== fps) { copy.frameRate = fps; }
    if (copy.pixelAspect !== par) { copy.pixelAspect = par; }
    if (copy.renderer !== renderer) { copy.renderer = renderer; }
    for (i = 0; i < plan.length; i++) {
        shifts.push(centerShift(plan[i].layer, time, copy.width, copy.height, plan[i].offset));
    }
    for (i = 0; i < plan.length; i++) {
        shift = shifts[i];
        moveBy(plan[i].layer, shift[0], shift[1]);
        moved++;
    }
    copy.time = saved;
    return {name: copy.name, width: whole(copy.width), height: whole(copy.height), layers: moved};
}

(function () {
    var a = CAVI_ARGS, comp, time, i, j, aspect, target, made = [], left = [];
    if (!a.aspects || !(a.aspects instanceof Array) || a.aspects.length < 1) { caviFail("at least 1 aspect"); }
    for (i = 0; i < a.aspects.length; i++) {
        aspect = a.aspects[i];
        aspectSize(aspect);
        for (j = i + 1; j < a.aspects.length; j++) {
            if (a.aspects[j] === aspect) { caviFail("aspects lists " + aspect + " twice"); }
        }
    }
    comp = caviComp(a.comp);
    for (i = 0; i < a.aspects.length; i++) {
        target = comp.name + " " + a.aspects[i];
        if (findComp(target)) { caviFail("A comp named " + target + " already exists"); }
    }
    time = a.time;
    if (time === undefined || time === null) { time = 0; }
    for (i = 0; i < a.aspects.length; i++) { made.push(reframeOne(comp, a.aspects[i], time, left)); }
    caviReport({comp: comp.name, comps: made, left: left, errors: []});
})();
