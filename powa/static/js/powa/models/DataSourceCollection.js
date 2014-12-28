define(['backbone', 'powa/models/DataSource'], function(Backbone, DataSource){
    return Backbone.Collection.extend({
        model: DataSource,

        update: function(from_date, to_date){
            this.each(function(datasource){
                datasource.update(from_date, to_date);
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
