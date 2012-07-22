/// some lifted utility functions
	function show(a) {
		$(a).style.display = 'block';
	}

	function hide(a) {
		$(a).style.display = 'none';
	}

	var $E = function(selector, filter) {
		return ($(filter) || document).getElement(selector);
	};

	var $ES = function(selector, filter) {
		return ($(filter) || document).getElements(selector);
	};

	function getWindowWidth() {
		if (window.innerWidth)
			return window.innerWidth;
		else
			return document.documentElement.clientWidth;
	}

	function getWindowHeight() {
		if (window.innerHeight)
			return window.innerHeight;
		else
			return document.documentElement.clientHeight;
	}


function generate_ajax_url(prefix
//		, extra_data
		) {
//	extra_data = extra_data || {};
	prefix = prefix || "";
	var n = new Hash( page_hash() );
//	n.extend(extra_data);
	var request_url = 'ajax/?' + prefix;
	var keys = Object.keys(n);
	
	for (var i = 0; i < keys.length; i++) {
		var key = keys[i];
		if (prefix.length == 0 && i == 0)
			request_url += key + '=' + n[key];
		else
			request_url += '&' + key + '=' + n[key];
	}

	return request_url
}


function make_checkable(data_table) {
	// select a tr element or a range of tr elements when the shift key is pressed
	selected_tr = ''
	$$('input.checker').addEvent('click', function(e) {
		last_selected_tr = selected_tr || '';
		var id =  e.target.getProperty('id');
		id = id.replace('check', 'row'); // id of equivalent <tr>
		selected_tr = $(id)
		if (e.shift && typeof(last_selected_tr) == 'object' && last_selected_tr != selected_tr){
			var checker_status;
			if (data_table.isSelected(last_selected_tr)) {
				data_table.selectRange(last_selected_tr, selected_tr);
				checker_status = true;
			}
			else if (data_table.isSelected(selected_tr)) {
				data_table.deselectRange(last_selected_tr, selected_tr);
				checker_status = false;
			}
			// (un)check the checkboxes
			var start_i; var end_i;
			var sel_tr_index = parseInt(id.split('_')[1])
			var last_sel_tr_index = parseInt(last_selected_tr.id.split('_')[1])
			if (sel_tr_index > last_sel_tr_index) {
				start_i = last_sel_tr_index;
				end_i = sel_tr_index;
			} else {
				start_i = sel_tr_index;
				end_i = last_sel_tr_index;
			}
			for (var j = start_i; j < (end_i + 1); j++){
				$('check_'+String(j)).setProperty('checked', checker_status);
			}
		} else {
			data_table.toggleRow(e.target.getParent('tr'));
		}		

	});
}


// for selecting and deselecting all the trs of a table
// state = true : ticks all checkboxes and selects all rows
// state = false : unticks all checkboxes and deselects all rows
function set_all_tr_state(context, state) {
	state ? context.selectAll() : context.selectNone();
	for (var i=0; i < $(context).getElements('tbody tr').length; i++) {
		$('check_'+i).setProperty('checked', state);
	}
}



function runXHRJavascript(){
//	console.log('runXHRJavaxript!');
	var scripts = $ES("script", 'tt-content');
	for (var i=0; i<scripts.length; i++) {
		// basic xss prevention
		if (scripts[i].get("ajaxKey") != _ajaxKey)
			continue;
		
		var toRun = scripts[i].get('html');
		var newScript = new Element("script");
		newScript.set("type", "text/javascript");
		if (!Browser.ie) {
			newScript.innerHTML = toRun;
		} else {
			newScript.text = toRun;
		}
		document.body.appendChild(newScript);
		document.body.removeChild(newScript);
	}
}


function redirectPage(context){
	nav.state.empty();
	nav.set(context);
	nav.fireEvent('navigationChanged', context);
}

function reloadPage(){
	var context = new Hash();
	context.extend(location.hash.replace("#",'').parseQueryString(false, true));
	redirectPage(context);
}

function showDialog(title, msg, options){
	var op = {'offsetTop': 0.2 * screen.availHeight};
	if (options) op = Object.merge(op, options)
	var SM = new SimpleModal(op);
	SM.show({
		'title': title, 
		'contents': msg
	});
	// add a max-height for modals
	// totally a hack
	$$('.simple-modal .contents')[0].setStyle('max-height', .60 * screen.availHeight);
	// center height of dialog
	var topOffset = (screen.availHeight -  $$('.simple-modal')[0].getSize().x) / 2;
	$$('.simple-modal')[0].setStyle('top', topOffset)
	return SM; // as a handle to work on this modal
}


// add a class of select to the current displayed menu
function highlightActiveMenu(){
	var aas = $$('.nav')[0].getElements('a');
	aas.each(function(item){
		if (location.hash.contains(item.hash)){
			item.getParent().addClass('active');
		}
	});
}

function disable_unimplemented_links(){
	// the current menus that have been implemented
	// this data structure is to be filled manually
	var implemented = {
		'hm': ['home', 'query', 'databases'],
		'db': ['overview', 'query'],
		'tbl': ['browse', 'structure', 'insert', 'query',]
	}
	var section = page_hash()['sctn']
	$$('.nav a').each(function(nav_link){
		if ( ! implemented[section].contains( nav_link.get('html').toLowerCase() ) ){
			new Element('span', {
				'style': 'display: block;float: none;line-height: 19px;padding: 10px 10px 11px;text-decoration: none;',
				'text': nav_link.get('html'),
				'alt': 'feature not yet implemented',
				'help': 'feature not yet implemented'
				}
			).replaces(nav_link)
		}
	});	
}

function page_hash(){
	return location.hash.replace('#','').parseQueryString(false, true);
}

// generate a where stmt for a selected row with index row_in in table tbl
function generate_where(tbl, row_in, for_post) {
	var stmt = "";
	if (!tbl.vars.keys) return stmt; // the table must have keys stored
	for_post = for_post || false;
	var delimitr = (for_post) ? "&" : "/i/AND/o/"; // the second delimtr is selected so
												   // - as to avoid collision with data
	var keys = tbl.vars.keys;
	for (var i = 0; i < keys.length; i++) {
		if (keys[i][0] == "") continue;
		// add quotes to the values, keys have not quotes
//		stmt += keys[i][0] + '=\'' + $ES('tbody tr', tbl)[row_in].getElements('td')[keys[i][2]].get('text');
//		stmt += (i != keys.length - 1) ? "\' {0} ".substitute([delimitr]) : "\'"; 
		stmt += keys[i][0] + '=' + $ES('tbody tr', tbl)[row_in].getElements('td')[keys[i][2]].get('text');
		stmt += (i != keys.length - 1) ? " {0} ".substitute([delimitr]) : ""; 
	}
	return stmt;
}

// generates a where stmt for all the selected rows in table tbl
function where_from_selected(tbl) {
	var stmt = "", selected_rows = tbl.getSelected();
	selected_rows.each(function(sel_row, sel_row_in){
		var id = parseInt(sel_row.id.replace('row_',''));
		stmt += generate_where(tbl, id);
		// if there are more rows add statement delimiter
		if (sel_row_in != selected_rows.length - 1)
			stmt += ';';
	});
	return stmt;
}

function tweenBgToWhite(el) {
	var elFx = new Fx.Tween($(el), {
		duration: 'long', 
		property: 'background-color',
		link: 'cancel'
	});
	elFx.start('#fff');
}


function show_block(ctrller, block_id) {
	// ctrller must be a clickable: button or input:submit
	
	ctrller.addEvent('click', function(e){
		e.stop();
		
		show( $(block_id) );
		ctrller.style.display = 'none';
	});
}

