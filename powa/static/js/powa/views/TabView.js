define([
        'backbone',
        'powa/views/WidgetView',
        'powa/models/TabContainer',
        'tpl!powa/templates/tabs.html']
function(Backbone, WidgetView, TabContainer, template){
    return WidgetView.extend({
        template: template,
        tag: "div",
        model: TabContainer,
        typname: "tabcontainer",
        initialize: function(args){
            this.model = args.model;
            this.tabs = this.model.get("tabs").map(WidgetView.makeView);
        },

        render: function(){
            this.$el.html(this.template(this.model.toJSON()));
            this.$tabtitles = this.$el.find(".tabs");
            this.$tabs = this.$el.find(".tabs-content");
            this.model.get("tabs").each(function(elem, index){
                var tabtitle = $("<li>").addClass("tab-title");
                if(index == 0){
                    tabtitle.addClass("active");
                }
                tabtitle.append($("<a>").attr("href", "#tab" + index).html(elem.get("title"));
                this.$tabtitles.append(tabtitle);
                var tabcontent = $("<div>").addClass("content").attr("id", "tab" + index);
                tabcontent.append(elem.widget.$el);
                this.$tabs.append(tabcontent);
            }, this);
            return this;
        }

    });

});

