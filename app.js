$(function() {
 
});

function add_material(e) {
  $("#new_material_modal").modal("show");

  var new_material = $($("#materials").children()[0]).clone();    
  $("#materials").append(new_material);
};

function material_selected(e) {
    var ref = e.target;
    alert($(ref).html());
};

function add_row(e) {
    var add_btn = e.target;
    var table_row = $(add_btn).parent().parent();
    var new_table_row = table_row.clone();
    table_row.parent().append(new_table_row);
};
