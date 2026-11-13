$.evalFile(new File(CAVI_LIB));

var MATCH = {casts_shadows: "ADBE Casts Shadows", light_transmission: "ADBE Light Transmission",
    accepts_shadows: "ADBE Accepts Shadows", accepts_lights: "ADBE Accepts Lights", shadow_color: "ADBE Shadow Color",
    appears_in_reflections: "ADBE Appears in Reflections", ambient: "ADBE Ambient Coefficient",
    diffuse: "ADBE Diffuse Coefficient", specular: "ADBE Specular Coefficient", shininess: "ADBE Shininess Coefficient",
    metal: "ADBE Metal Coefficient", reflection: "ADBE Reflection Coefficient", glossiness: "ADBE Glossiness Coefficient",
    fresnel: "ADBE Fresnel Coefficient", transparency: "ADBE Transparency Coefficient",
    transparency_rolloff: "ADBE Transp Rolloff", index_of_refraction: "ADBE Index of Refraction"};
var SHADOWS = {OFF: 0, ON: 1, ONLY: 2};

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), group, key, prop, value, shown = {};
    if (!caviIs3D(layer) || layer instanceof LightLayer || layer instanceof CameraLayer) {
        caviFail("Layer " + layer.name + " is not a 3D layer with material options");
    }
    group = layer.property("ADBE Material Options Group");
    if (!group) { caviFail("Layer " + layer.name + " has no material options"); }
    for (key in a.values) {
        prop = group.property(MATCH[key]);
        if (!prop) { caviFail("Layer " + layer.name + " has no material option " + key); }
        value = a.values[key];
        if (key === "casts_shadows") { value = caviEnum(SHADOWS, value, "casts_shadows"); }
        if (typeof value === "boolean") { value = value ? 1 : 0; }
        try {
            prop.setValue(value);
        } catch (unavailable) {
            caviFail("Material option " + key + " cannot be set on layer " + layer.name + " in a " + comp.renderer + " comp: " + String(unavailable));
        }
    }
    for (key in MATCH) {
        prop = group.property(MATCH[key]);
        if (prop) { shown[key] = prop.value; }
    }
    caviReport({comp: comp.name, layer: layer.name, renderer: comp.renderer, material: shown, errors: []});
})();
