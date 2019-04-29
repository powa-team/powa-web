define([
        'backbone',
        'powa/views/WidgetView',
        'powa/models/TabContainer',
        'tpl!powa/templates/tabs.html'],
function(Backbone, WidgetView, TabContainer, template){
    return WidgetView.extend({
        template: template,
        tag: "div",
        model: TabContainer,
        typname: "tabcontainer",
        initialize: function(args){
            this.model = args.model;
            this.tabs = this.model.get("tabs").map(WidgetView.makeView);
            this.datasources = new Backbone.Collection();
            _.each(this.tabs, function(tab){
                this.datasources.add(tab.model.data_sources.models);
            }, this);
            this.render();
        },

        render: function(){
            var self = this;
            this.$el.html(this.template(this.model.toJSON()));
            this.$tabtitles = this.$el.find(".tabs");
            this.$tabs = this.$el.find(".tabs-content");

            this.model.get("tabs").each(function(elem, index){
                var tabtitle = $("<li>").addClass("tab-title").attr("data-tabid", index);
                tabtitle.append($("<a>").attr("href", "#tab" + index).html(elem.get("title")));
                this.$tabtitles.append(tabtitle);
                var tabcontent = $("<div>").addClass("content").attr("id", "tab" + index);

                if(index == 0){
                    tabtitle.addClass("active");
                    tabcontent.addClass("active");
                }

                tabcontent.append(this.tabs[index].render().el);

                /* render the graphs on this tab right now.  This is not ideal
                 * as it slow donws inital display, but it avoids to render
                 * them at tab toggle time, which breaks the graph preview
                 * when a selection is done.
                 */
                tabcontent.show();

                /*
                 * The show() method will force a "display: block" style on the
                 * DOM element.  Override it with "inline-block" so elements
                 * are accumulated horizontally rather vertically, so the div
                 * keep its expected height.  The underlying CSS will take care
                 * of correct placement.
                 */
                tabcontent.attr('style', 'display: inline-block');

                this.$tabs.append(tabcontent);
            }, this);
            this.postRender();
            return this;
        },

        postRender: function(){
            this.$el.foundation();
        },


        refreshSources: function(startDate, endDate){
            this.datasources.each(function(data_source){
                if(data_source.get("enabled") != false){
                    data_source.update(startDate, endDate);
                }
            });
            this.updatePeriod(startDate, endDate);
        },
        updatePeriod: function(startDate, endDate){
            var self = this;
            if(startDate.isValid()){
                this.from_date = startDate;
            }
            if(endDate.isValid()){
                this.to_date = endDate;
            }
            _.each(this.tabs, function(tab){
                tab.updatePeriod(this.from_date, this.to_date);
            }, this);
        }

    });

});

