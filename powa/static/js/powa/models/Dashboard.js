define([
        'backbone',
        'powa/models/DataSourceCollection',
        'powa/models/Content',
        'powa/models/Grid',
        'powa/models/Wizard',
        'powa/models/Graph'
], function(
            Backbone,
            DataSourceCollection,
            Content,
            Grid,
            Wizard,
            Graph){
    return Backbone.Model.extend({
    }, {
        fromJSON: function(jsonobj){
            var tabs = new Backbone.Collection();
            _.each(jsonobj.tabs, function(tab, index){
                var widgets = new Backbone.Collection();
                _.each(tab.widgets, function(row, y){
                    _.each(row, function(widget, x){
                        widget.x = x;
                        widget.y = y;
                        if(widget.type == "graph"){
                            widgets.add(Graph.fromJSON(widget));
                        } else if (widget.type == "grid") {
                            widgets.add(Grid.fromJSON(widget));
                        } else if (widget.type == "content") {
                            widgets.add(Content.fromJSON(widget));
                        } else if (widget.type == "wizard") {
                            widgets.add(Wizard.fromJSON(widget));
                        }
                    });
                });
                tabs.add({'title': tab.title, 'widgets': widgets});
            });
            return new this({
                'title': jsonobj.title,
                'tabs': tabs});
        }
    });
});
