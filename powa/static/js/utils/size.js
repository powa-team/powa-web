export default {
  SizeFormatter: function (opts) {
    opts = opts || {};
    var suffix = opts.suffix;
    this.fromRaw = function (val) {
      if (val === undefined) {
        return "(NA)";
      }
      if (val === 0) {
        return "-";
      }
      if (val <= 1024) {
        return val.toFixed(2) + " " + "B";
      }
      var scale = [null, "K", "M", "G", "T", "P"];
      let i = 0;
      for (i; i < 5 && val > 1024; i++) {
        val /= 1024;
      }
      return val.toFixed(2) + " " + scale[i] + (suffix || "");
    };
  },
};
