odoo.define('ztyres.action_button', function (require) {
	"use strict";
	var ListController = require("web.ListController");
	ListController.include({
		renderButtons: function ($node) {
			var self = this;
			this._super($node)
			if (this.modelName === 'ztyres.wizard_update_pricelist') {
				console.log("Entra")
				this.model.get(this.handle, { raw: true }).context				
				console.log(this.$buttons.find(".o_list_export_xlsx").length)
				console.log(this.model.get(this.handle, { raw: true }).context)
					if (this.$buttons.find(".o_list_export_xlsx").length) {
						console.log("Entra2")
						var $export_xml_button = $("<button type='button' class='btn btn-primary fa fa-upload' data-original-title title>Importar archivo de Excel</button>");
						var $export_xml_button2 = $("<button type='button' class='btn btn-primary fa fa-check-circle-o' data-original-title title confirm='Are you sure to execute the automatic merge of your contacts ?'>Confirmar Importación de Precios</button>");
						this.$buttons.find(".o_list_export_xlsx").after($export_xml_button2);
						this.$buttons.find(".o_list_export_xlsx").after($export_xml_button);						
						console.log("Finaliza")

						
						this.$buttons.find('button.fa-upload').on('click', function (e) {
							e.preventDefault();
							// self.$buttons.find('button.fa-upload').hide();
							console.log("Click")
							console.log(this)
							console.log(e)
							return self.do_action({
								name: "Importar Lista de Precios",
								type: 'ir.actions.act_window',
								view_mode: 'form',
								views: [[false, 'form']],
								target: 'new',
								res_model: 'ztyres.update_pricelist_import',
								// context: { data: JSON.stringify(table) }
							});							
							
						}),

						
						this.$buttons.find('button.fa-check-circle-o').on('click', function (e) {
							e.preventDefault();k
							// self.$buttons.find('button.fa-upload').hide();
							console.log("Click")
							console.log(this)
							console.log(e)
							return self.do_action({
								name: "Comenzar Importación",
								type: 'ir.actions.act_window',
								view_mode: 'form',
								views: [[false, 'form']],
								target: 'new',
								res_model: 'ztyres.update_pricelist_confirm_import',
								// context: { data: JSON.stringify(table) }
							});							
							
						});
					}
			};
			console.log("_")
			
		},
		// _onButtonClick: function (event) {
		// 	console.log(event)
		// 	console.log("Click 1")
		// 	var $target = $(event.target);
		// 	if ($target.hasClass('fa-upload')) {
		// 		console.log("Click 2")
		// 		this._AgregarMonto();
		// 	}
		// 	else {
		// 		this._super(event);
		// 		console.log("Click 3")
		// 	}
		// },
		// _AgregarMonto: function () {
		// 	var table = this.model.exportData();
		// 	return this.do_action({
		// 		name: "Agregar Monto Flujo de Efectivo",
		// 		type: 'ir.actions.act_window',
		// 		view_mode: 'form',
		// 		views: [[false, 'form']],
		// 		target: 'new',
		// 		res_model: 'ztyres.update_pricelist_import',
		// 		context: { data: JSON.stringify(table) }
		// 	});
		// },
	})
});


