$.evalFile(new File(CAVI_LIB));

function option(layer, group, name, value) {
    if (value !== null && value !== undefined) { caviSetStatic(caviProp(layer, group + "/" + name), value); }
}

function camera(comp, c, rig) {
    var layer, zoom = c.zoom, nulled, poi;
    if (c.layer !== null) {
        layer = caviLayer(comp, c.layer);
        if (!(layer instanceof CameraLayer)) { caviFail("Layer " + layer.name + " is not a camera"); }
    } else {
        layer = comp.layers.addCamera(c.name, [comp.width / 2, comp.height / 2]);
        layer.name = c.name;
    }
    if (c.nodes === 1) { layer.autoOrient = AutoOrientType.NO_AUTO_ORIENT; }
    if (c.nodes === 2) { layer.autoOrient = AutoOrientType.CAMERA_OR_POINT_OF_INTEREST; }
    if (c.focal_length !== null) { zoom = c.focal_length * comp.width / 36; }
    option(layer, "Camera Options", "Zoom", zoom);
    option(layer, "Camera Options", "Depth of Field", c.depth_of_field === null ? null : (c.depth_of_field ? 1 : 0));
    option(layer, "Camera Options", "Focus Distance", c.focus_distance);
    option(layer, "Camera Options", "Aperture", c.aperture);
    option(layer, "Camera Options", "Blur Level", c.blur_level);
    if (c.position !== null) { caviSetStatic(caviProp(layer, "position"), c.position); }
    if (c.point_of_interest !== null) { caviSetStatic(caviProp(layer, "Transform/Point of Interest"), c.point_of_interest); }
    if (rig) {
        poi = layer.autoOrient === AutoOrientType.CAMERA_OR_POINT_OF_INTEREST ?
            layer.property("ADBE Transform Group").property("ADBE Anchor Point").value : [comp.width / 2, comp.height / 2, 0];
        nulled = comp.layers.addNull(comp.duration);
        nulled.name = layer.name + " Orbit";
        nulled.threeDLayer = true;
        nulled.property("ADBE Transform Group").property("ADBE Position").setValue(poi);
        layer.parent = nulled;
    }
    return layer;
}

function light(comp, l) {
    var layer, types = {POINT: LightType.POINT, SPOT: LightType.SPOT, PARALLEL: LightType.PARALLEL, AMBIENT: LightType.AMBIENT,
        ENVIRONMENT: LightType.ENVIRONMENT};
    if (l.layer !== null) {
        layer = caviLayer(comp, l.layer);
        if (!(layer instanceof LightLayer)) { caviFail("Layer " + layer.name + " is not a light"); }
    } else {
        layer = comp.layers.addLight(l.name, [comp.width / 2, comp.height / 2]);
        layer.name = l.name;
    }
    if (l.type !== null) { layer.lightType = caviEnum(types, l.type, "light type"); }
    option(layer, "Light Options", "Intensity", l.intensity);
    option(layer, "Light Options", "Color", l.color);
    option(layer, "Light Options", "Cone Angle", l.cone_angle);
    option(layer, "Light Options", "Cone Feather", l.cone_feather);
    option(layer, "Light Options", "Casts Shadows", l.casts_shadows === null ? null : (l.casts_shadows ? 1 : 0));
    option(layer, "Light Options", "Shadow Darkness", l.shadow_darkness);
    option(layer, "Light Options", "Shadow Diffusion", l.shadow_diffusion);
    if (l.position !== null) { caviSetStatic(caviProp(layer, "position"), l.position); }
    if (l.point_of_interest !== null) { caviSetStatic(caviProp(layer, "Transform/Point of Interest"), l.point_of_interest); }
    return layer;
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), report = {comp: comp.name, errors: []}, cam, lit, opts;
    if (a.camera !== null) {
        cam = camera(comp, a.camera, a.rig);
        opts = cam.property("ADBE Camera Options Group");
        report.camera = describeLayer(cam);
        report.camera.nodes = cam.autoOrient === AutoOrientType.CAMERA_OR_POINT_OF_INTEREST ? 2 : 1;
        report.camera.zoom = opts.property("ADBE Camera Zoom").value;
        report.camera.depth_of_field = opts.property("ADBE Camera Depth of Field").value;
        report.camera.focus_distance = opts.property("ADBE Camera Focus Distance").value;
        report.camera.aperture = opts.property("ADBE Camera Aperture").value;
        report.camera.blur_level = opts.property("ADBE Camera Blur Level").value;
        report.camera.position = cam.property("ADBE Transform Group").property("ADBE Position").value;
    }
    if (a.light !== null) {
        lit = light(comp, a.light);
        opts = lit.property("ADBE Light Options Group");
        report.light = describeLayer(lit);
        report.light.light_type = String(lit.lightType);
        report.light.intensity = opts.property("ADBE Light Intensity").value;
        report.light.casts_shadows = opts.property("ADBE Casts Shadows").value;
    }
    caviReport(report);
})();
