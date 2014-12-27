define([], function(){
    return {
        SizeFormatter: function(opts){
            opts = opts || {};
            this.suffix = opts.suffix;
            this.fromRaw = function(val){
                if(val === undefined){
                    return "(NA)"
                }
                if (val <= 1024) { return val + ' ' + 'B'; }
                var scale = [null, 'Ki', 'Mi', 'Gi', 'Ti', 'Pi'];
                for (i=0; i<5 && val > 1024; i++) {
                    val /= 1024;
                }
                return val.toFixed(2) + ' ' + scale[i] + this.suffix || "";
            }
        }
    }
});
