$.evalFile(new File(CAVI_LIB));

(function () {
    var wanted = CAVI_ARGS.match_names, have = {}, i, found = [];
    for (i = 0; i < app.effects.length; i++) {
        have[app.effects[i].matchName] = true;
    }
    for (i = 0; i < wanted.length; i++) {
        found.push({match_name: wanted[i], available: have[wanted[i]] === true});
    }
    caviReport({effects: found, errors: []});
})();
