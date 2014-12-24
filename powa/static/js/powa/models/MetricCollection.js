define(['backbone', 'powa/models/Metric'], function(Backbone, Metric){
    return Backbone.Collection.extend({
        model: Metric,

        initialize: function(){
        },
    });
});
