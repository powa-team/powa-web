define(['backbone', 'powa/models/MetricGroup'], function(Backbone, MetricGroup){
    return Backbone.Collection.extend({
        model: MetricGroup,

        update: function(from_date, to_date){
            this.each(function(metricgroup){
                metricgroup.update(from_date, to_date);
            });
        }

    }, {
        get_instance: function(){
            if(this._instance === undefined){
                this._instance = new this();
            }
            return this._instance;
        }
    });
});
