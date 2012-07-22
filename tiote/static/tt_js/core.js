var pg, nav; // global variables
var assets = new Hash(); // very funny store

function navigationChangedListener(navObject, oldNavObject){
	// redirect to the next page as gotten from the location hash
	if (Cookie.read('TT_NEXT')){
		navObject = Cookie.read('TT_NEXT').parseQueryString(false, true);
		location.hash = '#' + Cookie.read('TT_NEXT');
		Cookie.dispose('TT_NEXT');
	}
	// create a new Page object which begins page rendering
	pg = new Page(navObject, oldNavObject);
}

window.addEvent('domready', function() {
	preloadImages();
	nav = new Navigation();	
	nav.addEvent('navigationChanged', navigationChangedListener);
	
	// make the string representation of all the abbreviations in use a JSON object
	// the value and the key are associated by their index so they should not be changed
	_abbrev = new Object();
	_abbrev['keys'] = JSON.decode(_abbrev_keys);
	_abbrev['values'] = JSON.decode(_abbrev_values);
	delete _abbrev_keys;delete _abbrev_values; // maybe it will reduce memory (so c++)
	
	// if the location string contains hash tags
	if (location.hash) {
		// begin page rendering
		var navObj = page_hash();
		pg = new Page(navObj, null);
	}
	// there are no hashes set a default
	else
		nav.set({'sctn': 'hm', 'v': 'hm'});
	// higlight the element (.navbar a) that corresponds to the currently displayed view

});


/*
 * make UI images accessible by the DOM before they are required
 * 
 * notice: to make sure this list is accurate and doesn't generate funny 404 errors: 
 * to update the images collection below use a list generated from reading the contents
 * of the directory containing the images (python was used here)
 */
function preloadImages() {
	var images = ['schemas.png', 'sequences.png', 'sortdesc.gif', 'table.png', 'sequence.png',
		'tables.png', 'databases.png', 'views.png', 'spinner.gif', 'database.png', 'goto.png',
		'schema.png', 'sortasc.gif'
	];
	
	var pre;
	for (var i=0; i<images.length; i++) {
		pre = new Image();
		pre.src = _staticUrl + "tt_img/" + images[i];
	}	
}


// A single tiote page
function Page(obj, oldObj){
	this.options = new Hash({navObj: obj, oldNavObj: oldObj});
	this.tbls = [];
	// unset all window resize events
	window.removeEvents(['resize']);
	this.clearPage();
	this.loadPage(true);
}

Page.prototype.clearPage = function(clr_sidebar) {
	clr_sidebar = clr_sidebar || false; // init
	if (clr_sidebar && $('sidebar').getChildren()) {
		$('sidebar').getChildren().destroy();
	}
	$('tt-content').getChildren().destroy();
}

Page.prototype.loadPage = function(clr_sidebar) {
	clr_sidebar = clr_sidebar || false;
	var obj = this.options.navObj, oldObj = this.options.oldNavObj;
	this.updateTitle();
	this.updateTopMenu(obj);
	disable_unimplemented_links();
	this.generateView(obj, oldObj); 
	this.generateSidebar(clr_sidebar);
	highlightActiveMenu();
}


/*
 * Generates the title of the current page from location.hash
 * It follows the following format
 *
 *		tiote / view [ / subview ] :  / database [ / schm  ]/ table [/ subv] [/ page ]
 */
Page.prototype.updateTitle = function(new_title){
	new_title = new_title || false;
	if (! new_title) {
		var title = 'tiote';
		var r = location.hash.replace('#','').parseQueryString();
		// if the key can be translated translate else leave as it is
		var _in = _abbrev.keys.indexOf(r['v']);
		if (_in != -1)
			title += ' / ' + _abbrev.values[_in];
		else
			title += ' / ' + r['v'];
		// append spilter to the title of the page
		//- functions(more like navigation depth) : objects ( db or tbl or schm we are working on)
		title += " :";
		['db','schm','tbl'].each(function(or_item){
			if (Object.keys(r).contains(or_item)) title += ' / ' + r[or_item];
		});
		if (Object.keys(r).contains('offset')) title += ' / page ' + (r['offset'] / 100 + 1);
		if (Object.keys(r).contains('subv')) {
			// basic assumption made here: all subvs are abbreviations
			_in = _abbrev.keys.indexOf(r['subv']);
			title += ' / ' + _abbrev.values[_in];
		}
	} else {
		title = new_title;
	}
	document.title = title
	this.updateOptions({'title': title});
}

Page.prototype.updateTopMenu = function(data){
	var links = new Hash();
	// all the links that can be displayed in the top menu
	var l = ['query', 'import', 'export', 'insert', 'structure', 'overview',
		'browse', 'update', 'search', 'home', 'users', 'databases', 'operations'];
	
	l.each(function(item){
		links[item] = new Element('a', {'text': item});
	});
	
	// describe the links and their order that would be displayed in the top menu
	// - also theirs sections and possible keys needed to complete the url
	var order = [];var prefix_str;var suffix;
	if (data['sctn'] == 'hm') {
		order = ['home', 'users', 'databases' ,'query', 'import', 'export'];
		prefix_str = '#sctn=hm';
	} else if (data['sctn'] == 'db') {
		order = ['overview', 'query','import','export'];
		prefix_str = '#sctn=db';
		suffix = ['&db=']
	} else if (data['sctn'] == 'tbl') {
		order = ['browse', 'structure', 'insert', 'operations', 'query', 'import', 'export'];
		prefix_str = '#sctn=tbl';
		suffix = ['&db=','&tbl='];
	}
	
	var aggregate_links = new Elements();
	order.each(function(item, key){
		var elmt = links[item];
		// set the href tags of all the links
		// view placeholders need some processing
		var _in = _abbrev.values.indexOf(elmt.text);
		if ( _in != -1){
			// any such view should have its href v placeholder to be shortened
			elmt.href = prefix_str + '&v=' + _abbrev.keys[_in];
		}
		else
			elmt.href = prefix_str + '&v=' + elmt.text;
		
        if (data['sctn'] == 'db' || data['sctn'] == 'tbl'){
            elmt.href += suffix[0] + data['db'];
            if (data['schm'])
                elmt.href += '&schm=' + data['schm'];
        }
        if (data['sctn'] == 'tbl')
            elmt.href += suffix[1] + data['tbl'];
		// todo: add suffix_str eg &tbl=weed
		elmt.text = elmt.text.capitalize();
		var ela = new Element('li',{});
		ela.adopt(elmt);
		aggregate_links.include(ela);
	});
	
	var nava = new Element('ul',{'class':'nav'}); 
	if ($$('div.topbar ul.nav'))	$$('div.topbar ul.nav')[0].destroy();
	aggregate_links.inject(nava);
	$$('.topbar .container-fluid')[0].adopt(nava);
}

Page.prototype.generateView = function(navObj, oldNavObj){
//	console.log(navObj), console.log(oldNavObj);
	new XHR({
		url: generate_ajax_url(), 
		method: 'GET',
		onSuccess: function(text, xml) {
			if (Cookie.read('TT_NEXT')){
				// don't understand why but this cookie is usually appended with 
				// - quotes at the beginning and at the end (not its representation)
				var o = Cookie.read('TT_NEXT').parseQueryString(true, true);
				var o2 = {};
				Object.keys(o).each(function(k){
					o2[ k.replace("\"", "") ] = o[k].replace("\"",'');
				});
				Cookie.dispose('TT_NEXT');
				redirectPage(o2);
				return;
			}
			$('tt-content').set('html', text);
			if (navObj['sctn']=='tbl' && navObj['v'] =='browse') {
				pg.jsifyTable(true);
				pg.browseView();
			} else {pg.jsifyTable(false);}
			pg.addTableOpts();
			// attach events to forms
			if ($$('.tt_form')) {pg.completeForm();}
			runXHRJavascript();
		}
	}).send();
}

// decide if the sidebar needs to be refreshed
function canUpdateSidebar(navObj, oldNavObj) {
	var clear_sidebar = false; // default action is not to clear the sidebar
	if (Cookie.read('TT_UPDATE_SIDEBAR')){
		clear_sidebar = true;
		Cookie.dispose('TT_UPDATE_SIDEBAR');
	} else {
		// other necessary conditions
		// if the #sidebar element is empty reload the sidebar
		if ($('sidebar') && $('sidebar').getChildren().length) {
			if (oldNavObj == undefined || oldNavObj == null || oldNavObj == "")
				return clear_sidebar; // short circuit the function
			
		// if there is no percievable change in the location.hash of the page
		// - dont clear sidebar
		if (oldNavObj['sctn'] == navObj['sctn'] && oldNavObj['tbl'] == navObj['tbl']
			&& oldNavObj['db'] == navObj['db']
		) {
			// check if the hash obj contains a schema key
			if (Object.keys(oldNavObj).contains('schm') && Object.keys(navObj).contains('schm')) {
				// postgresql dialect
				if (oldNavObj['schm'] == navObj['schm']) clear_sidebar = false;
			} else {
				// mysql dialect
				clear_sidebar = false;
			}
		}
		}
	}
	return clear_sidebar;
}

Page.prototype.generateSidebar = function(clear_sidebar) {
	
	var resize_sidebar = function() {
		// basic assumption here is that there is one ul and that one is a long one
		// autosize the sidebar to the available height after below the #topbar
		var sidebar_height = getHeight() - 50; // 50 for the div immediately under #topbar
		$('sidebar').setStyle('height', sidebar_height);
		// only the ul elements should be scrollable when it exceeds the size of the sidebar
		var inner_ul = $E('#sidebar ul');
		// there are times when sidebar has no ul in it
		if (inner_ul == null)
 			return;
		
		inner_ul.setStyle('height', null); // resets the height to broswer computed values
		// siblings_height is height of all the ul's siblings [selects, h5.placeholders e.t.c]
		var siblings_height = $('sidebar').getScrollSize().y - inner_ul.getSize().y
		inner_ul.setStyle('height', getWindowHeight() - 40 -  siblings_height);
	};
	
	// decide if there should be a sidebar update
	// if clear_sidebar is already true then there must be a sidebar update
	// - if it isn't decide from the context of the current view if there should be
	clear_sidebar = clear_sidebar || false;
	var navObj = this.options.navObj, oldNavObj = this.options.oldNavObj;
	if (!clear_sidebar)
		clear_sidebar = canUpdateSidebar(navObj, oldNavObj);
	
	if (clear_sidebar != true) return;
	
	new XHR({
		url : generate_ajax_url('q=sidebar&type=repr'),
		method: 'get',
		onSuccess: function(text,xml){
			// if the sidebar contains elements destroy them
			if ($('sidebar').getChildren())
				$('sidebar').getChildren().destroy();
			$('sidebar').set('html', text);
			window.addEvent('resize', resize_sidebar);
			window.fireEvent('resize'); // fire immediately to call resize handler
			// handle events
			var _o = page_hash();
			// makes the select elements in the sidebar redirect to a new and appropriate view
			// when its value is changed. the new view depends on the final value of the select element
			$('sidebar').getElements('#db_select, #schema_select').addEvent('change', function(e){
				var sp_case = e.target.id == 'db_select' ? 'db': 'schm'; //special_case is the only
																			// key that changes
				if (e.target.value != _o[sp_case]) {
					var context = Object.merge(page_hash(), {'sctn': 'db', 'v': 'ov'});
					context[sp_case] = e.target.value;
					location.hash = '#' + Object.toQueryString(context);
				}
			});
			// highlights the link corresponding to the current view in the sidebar
			//  in cases where the sidebar wasn't refreshed
			$$('#sidebar ul a').addEvent('click', function(e){
				$$('#sidebar ul li').removeClass('active');
				e.target.getParent().addClass('active');
			});
			// provide sidebar navigation which keeps the view information of the last page
			// i.e. other keys of the location.hash is kept besides the special cases
			$('sidebar').getElements('.schm-link, .tbl-link').addEvent('click', function(e){
				e.stop(); // stops default behaviour: navigation
				var sp_case = e.target.hasClass('schm-link') ? 'schm': 'tbl'; //special_case is the only
																				// key that changes
				var context = page_hash()
				context[sp_case] = e.target.get('text');
				// removes the keys [sort_key and sort_dir]
				// they introduce errors in browse view. sorting by columns that don't exist
				// - when the navigation is changed to another table
				['sort_key', 'sort_dir', 'pg', 'offset'].each(function(_it){ // unwanted keys: manually update
					if (Object.keys(context).contains(_it))
						delete context[_it];
				});
				if (context[sp_case] != _o[sp_case]) {
					location.hash = '#' + Object.toQueryString(context);
				}
			});
		}
	}).send();
		
	window.addEvent('resize', resize_sidebar);
	window.fireEvent('resize'); // fire immediately to call resize handler
}


Page.prototype.jsifyTable = function(syncHeightWithWindow) {
	// display
	$$('.jsifyTable').each(function(cont, cont_in) {
//		console.log('cont #' + cont_in);
		// auto update height
		syncHeightWithWindow = syncHeightWithWindow || false;
		if (syncHeightWithWindow) {
			window.addEvent('resize', function() {
				if ($E('.tbl-body table', cont) != null) {
					var t = $E('.tbl-body table', cont);
					if (t.getScrollSize().y > (getHeight() - 110)) {
						t.setStyle('height', (getHeight() - 110));
					} else {
						t.setStyle('height', null);
					}
				}
			});
			window.fireEvent('resize');
		}
		if (cont.getElements('.tbl-body table tr').length) {
			// same size body and header
			var tds = cont.getElements('.tbl-body table tr')[0].getElements('td');
			var ths = cont.getElements('.tbl-header table tr')[0].getElements('td');

			for (var i = 0; i < ths.length - 1; ++i) {
				var width;
				if (ths[i].getDimensions().x > tds[i].getDimensions().x) {
					width = ths[i].getDimensions().x + 10;
					tds[i].setStyles({'min-width':width, 'width': width});
					width = tds[i].getDimensions().x - 1; // -1 for border
					ths[i].setStyles({'min-width': width, 'width': width});
				} else {
					width = tds[i].getDimensions().x - 1; // -1 for border
					ths[i].setStyles({'min-width': width, 'width': width});
				}
			}
			tds = null, ths = null;
		}
		// sync scrolling of 'tbl-body table' with '.tbl-header tbl'
		if (cont.getElement('.tbl-body table') != undefined
			&& cont.getElement('.tbl-header table') != undefined) {
			// variables needed
			var tblhead_tbl = cont.getElement('.tbl-header table');
			var tblbody_tbl = cont.getElement('.tbl-body table');
			// sync scrolling 
			tblbody_tbl.addEvent('scroll', function(e){
				var scrl = tblbody_tbl.getScroll();
				cont.getElement('.tbl-header table').scrollTo(scrl.x, scrl.y);
			});
			// add the width of scrollbar to min-width property of ".tbl-header td.last-td"
			var w = tblbody_tbl.getScrollSize().x - tblhead_tbl.getScrollSize().x;
			w = w + 25 + 7; // magic numbers they worked though;
			tblhead_tbl.getElement('td.last-td').setStyle('min-width', w);	
		}
	});
	
	// behaviour
	var tbls = $$('table.sql');
	for (var tbl_in= 0 ; tbl_in < tbls.length; tbl_in++) {
		var tbl = tbls[tbl_in];
		var html_table = new HtmlTable($(tbl))
		pg.tbls.include(html_table);
		make_checkable(html_table);
		// attach the variables passed down as javascript objects to the 
		// table object
		html_table['vars'] = {}; var data;// containers

		if (tbl.get('data')) {
			data = {}
			tbl.get('data').split(';').each(function(d){
				var ar = d.split(':');
				data[ar[0]] = ar[1];
			});
			html_table['vars']['data'] = data; // schema: [key: value]
		}
		
		if (! tbl.get('keys'))
			continue; // this conditions is needed to go on till end of loop
		
		data = []; // data[[0,1,2],...] indexes 0: name of column,
						// 1 : index type
						// 2 : column position in tr
		tbl.get('keys').split(';').each(function(d){
			var ar = d.split(':');
			if (ar[0] != "") data.include(ar);
		});
		// loop through the tds int .tbl-header to see which corresponds to the keys
		$$('.tbl-header table')[tbl_in].getElements('td').each(function(th, th_in){
			for (var i = 0; i < data.length; i++) {
				var _colname = $E('div span.column-name', th);
				if (_colname == null) 
					continue;
				if (_colname.get('text') == data[i][0] )
					data[i].include(th_in);
			}
		});

		html_table['vars']['keys'] = data; // schema: [column, key_type, column index]

		// handle a.display_row(s) click events
		tbl.getElements('a.display_row').addEvent('click', function(e) {
			var al_in = parseInt( e.target.getParent('tr').id.replace('row_', '') );
			var where_stmt = generate_where(html_table, al_in, true);
			// make xhr request
			new XHR({
				url: generate_ajax_url('q=get_row&type=fn') ,
				spinnerTarget: tbl,
				onSuccess : function(text, xml) {
					showDialog("Entry", text, {
						offsetTop: null, width: 475, hideFooter: true,
						overlayOpacity: 0, overlayClick: false
					});
				}
			}).post(where_stmt);
		});

	}

}


function tbl_pagination(total_count, limit, curindex) {
	curindex = parseInt(curindex);	// enables arithmetic meaning
	var maxindex = 1 + Math.floor(total_count / limit); // maxindex must start from 1
	var _o = page_hash();
	
	var p = '<p class="paginatn pull-right">';	// pagination elements container
	var info_span = '<span style="padding-left:15px">[ {0} {1} ]</span>'.substitute([
		total_count, total_count > 1 ? 'rows' : 'row'
	]);
	
	if (maxindex == 1) // necessary condition to continue
		return p + info_span + '</p>';

	// generate select element
	var selindex_elmt = '<select id="index-select" style="width:45px; padding:1px; height:22px;">'
	for (var i = 1; i < (maxindex + 1); i++) {	// one more off the maxindex since counting starts from 1
		selindex_elmt += '<option value="{i}" {sel}>{i}</option>'.substitute({
			'i':i, 
			sel: i == curindex ? 'selected="selected"' : ''
		});
	}
	selindex_elmt += '</select>';
	// generate pagination links
	var els = [];
	var anc_template = '<a class="pag_lnk cntrl" href="{href}">{text}</a>';

	if (curindex != 1) {
	// add a previous link
		_o['pg'] = curindex - 1;
		els.include(anc_template.substitute({
			text: 'previous', href: '#' + Object.toQueryString(_o)
		}));
		if (curindex != maxindex)
			els.include('<span class="seperator">|</span>'); // seperator
	}
	if (curindex != maxindex) {
		// add a next link
		_o['pg'] = curindex + 1;
		els.include(anc_template.substitute({
			text: 'next', href: '#' + Object.toQueryString(_o)
		}));
	}
	// the select elmt
	els.include(selindex_elmt);
	// done
	return p + els.join('') + info_span + '</p>';
}


Page.prototype.addTableOpts = function() {
	// .table-options processing : row selection
	if ($$('.table-options') == null || ! Object.keys(pg.tbls).length)
		return;
	
	$$('.table-options').each(function(tbl_opt, opt_in){
		var htm_tbl = pg.tbls[opt_in]; // short and understandable alias

		// table's needing pagination
		// this sequence is placed first so as not invalidate event handlers placed on some html elements
		if (Object.keys(htm_tbl.vars).contains('data')) {
			var pg_htm = tbl_pagination( // pagination html
				htm_tbl.vars.data['total_count'],
				htm_tbl.vars.data['limit'], 
				htm_tbl.vars.data['pg']
			);
			$(tbl_opt).getElement('p').innerHTML += pg_htm;
		}
		// add interactivity to the select element in the tables' pagination
		$ES('select#index-select', tbl_opt).addEvent('change', function(e){
			var nextpg = e.target.get('value'), _o = page_hash();
			if ((Object.keys(_o).contains('pg') && _o[pg] != nextpg) || (nextpg != 1) ){
				_o['pg'] = nextpg;
				location.hash = '#' + Object.toQueryString(_o);
			}
			
		});

		// enable selection of rows
		$(tbl_opt).getElements('a.selector').addEvent('click', function(e) {	
			// loop through all the classes to find the "select_" class
			e.target.get('class').split(' ').each(function(cl){
				if (cl.contains('select_')) {
					var option = cl.replace('select_', '').toLowerCase();
					set_all_tr_state(htm_tbl, (option == 'all') ? true : false);
				}
			});
		});

	// links that do something (edit, delete ...)
		tbl_opt.getElements('a.doer').addEvent('click', function(e){
			e.stop();
			if (e.target.hasClass('action_refresh'))
				// action to be performed is a page refresh
//				pg.loadPage(false)
				reloadPage();
			else 
				do_action_wrapper(htm_tbl, e);
		});

		// disable or enable if no row is selected or rows are selected respectively.
		var needy_doer_options = function(tr, tr_all) {
			if (tr_all.length) {
				$$('a.needy_doer').setStyles({
					'color': '#0069D6',
					'cursor': 'pointer'
				});
			} else {
				$$('a.needy_doer').setStyles({
					'color': '#888', 
					'cursor': 'default'
				});
			}
		}

		htm_tbl.addEvent('rowFocus', needy_doer_options).addEvent('rowUnfocus', needy_doer_options);

	});
	
}

function edit_view(where_stmt) {
	// make xhr query for edit form
	new XHR({
		url: generate_ajax_url() + '&subv=edit',
		spinTarget: $('tt_content'),
		onSuccess: function(text, xml) {
//			$('tt-content').set('html', text);
			var sm_obj = showDialog('edit',	text, {
				hideFooter: true, closeOnEsc: true,
				overlayClick: false , width: '450px'
			});
			Cookie.write("tt_edit_form", 'true');
			pg.completeForm(sm_obj);
		}
	}).post({where_stmt: where_stmt});
}


function do_action_wrapper(tbl, e) {
	if (! tbl.getSelected().length )// necessary condition to begin
		return;

	// control decider
	var can_do_action = false;
	// determine the action to be performed
	var action = '';
	var clses= e.target.get('class').split(' ');
	for (var _in= 0; _in < clses.length; _in++) {
		var cls = clses[_in]
		if (! cls.contains('action_'))
			continue
		action = cls.replace("action_", "");
	}
	/// generate msg to be displayed in the dialog
	/// while generating the msg determine if the action does not need further confirmation
	/// probably if the action doesn't pose serious unchangeable side effects
		var msg = "Are you sure you want to " + action + " the selected ";
		var where_stmt = where_from_selected(tbl); // string to be posted
		var navObject = page_hash();
		// update the dialog message to include the specific type of object 
		// and pluralize if more than one object is to worked upon
		if (navObject['sctn'] == "db") {
			if (Object.keys(navObject).contains('subv') && navObject['subv'] == 'seqs')
				if (action == 'reset')
					can_do_action = true
				else
					msg += where_stmt.contains(';') ? "sequences" : "sequence";
			else
				// default situation. translates to tbl view of section db
				msg += where_stmt.contains(';') ? "tables" : "table";
		}
		else if (navObject['sctn'] == "tbl") {
			if (navObject['v'] == 'browse')
				// deletn and dropping of data is not really a very bad thing
				can_do_action = true;
//				msg += where_stmt.contains(';') ? "rows" : "row";
			else if (navObject['v'] == 'struct') {
				if (! action in ['delete', 'drop'])
					can_do_action = true;
				else if (navObject['subv'] == 'idxs')
					msg += where_stmt.contains(';') ? 'indexes': 'index';
				else if (navObject['subv'] == 'cons')
					msg += where_stmt.contains(';') ? 'constraints': 'constraint';
				else
					// it defaults to columns if there is no subv or the subv contains 'cols'
					msg += where_stmt.contains(';') ? 'columns': 'column';
			}
		}
		else if (navObject['sctn'] == 'hm' && navObject['v'] == "dbs")
			msg += where_stmt.contains(";") ? "databases": "database";
	
	// local function that provides a way to pass local variables to a non-local function
	var do_action_caller = function() {
		do_action(action, where_stmt, tbl);
	}
	
	/// check if can_do_action has been set to true when generating the message.
	/// if it has then just do the action, if it hasn't then confirm if the selected
	/// action is desirable
		if (can_do_action)
			do_action_caller();
		else {
			// confirm if intention is to be carried out
			var confirmDiag = new SimpleModal({'btn_ok': 'Yes', overlayClick: false,
				draggable: true, offsetTop: 0.2 * screen.availHeight
			});
			confirmDiag.show({
				model: 'confirm',
				callback: do_action_caller, 
				title: 'Confirm intent',
				contents: msg
			});		
		}
}


function do_action(action, where_stmt, tbl) {
	if (action == 'edit') {
		edit_view(where_stmt);
	} else {
		new XHR({
			url: generate_ajax_url() + '&upd8=' + action,
			spinnerTarget: $(tbl), 
			onSuccess: function(text, xml) {
				var resp = JSON.decode(text);
				if (resp['status'] == "fail") {
					showDialog("Action not successful", resp['msg']);
				} else if (resp['status'] == 'success')
					reloadPage();
			}
		}).post({'where_stmt': where_stmt});
	}	
}


Page.prototype.browseView = function() {	
	if (! document.getElement('.tbl-header')) 
		return;
	
	var theads = document.getElement('.tbl-header table tr').getElements('td[class!=controls]');
	theads.setStyle('cursor', 'pointer');
	theads.each(function(thead, thead_in){
		// add click event
		thead.addEvent('click', function(e){
			var _colname = $E('div span.column-name', thead);
			var key = (_colname) ? _colname.get('text') : '';
			var o = page_hash(); var dir = '';
			if (o.sort_key != undefined && o.sort_key != key ) {
				dir = 'asc'
			} else {
				if (o.sort_dir == 'asc') dir = 'desc';
				else if (o.sort_dir == 'desc') dir = 'asc';
				else dir = 'asc';
			}
			o['sort_dir'] = dir;o['sort_key'] = key;
			location.hash = "#" + Object.toQueryString(o);
		});
		// mark as sort key
		if (thead.get('text') == page_hash()['sort_key']) {
			thead.setStyle('font-weight', 'bold');
			thead.addClass(page_hash()['sort_dir'] == 'asc'? 'sort-asc': 'sort-desc');
		}
	});
}

Page.prototype.updateOptions = function(obj) {
	this.options.extend(obj)
}

Page.prototype.reload = function() {
	this.loadPage();
}


// function that is called on on every form request
function formResponseListener(text, xml, form, n_obj, dialog_handler) {
	$E('.msg-placeholder').getChildren().destroy();
	if (n_obj['v'] == 'q') {
		$E('.query-results').set('html', text);
		if ($E('.query-results').getElement('div.alert-message')) {
			tweenBgToWhite($E('.query-results div.alert-message'))
		}
		pg.jsifyTable();
		return; // end this function here
	}
	var resp = JSON.decode(text);
	if (resp['status'] == 'success'){
		if (Cookie.read('tt_edit_form')) {
			$(form).destroy(); // destroy the current edit form
			if (!$$('.tt_form').length) {
				// if there are no more forms close the edit dialog
				dialog_handler.hide();
				Cookie.dispose('tt_edit_form');
				// reload the view to update tables
//				pg.loadPage(); // some events are called (means not attached)
				reloadPage(page_hash());
			}
		}
		else 
			form.reset(); // delete the input values
	}
	
	var html = ("" + resp['msg']).replace("\n","&nbsp;");
	if (n_obj['v']!= 'q') {
		$E('.msg-placeholder').set('html', html);
		tweenBgToWhite($E('.msg-placeholder').getElement('div.alert-message'))
	}
	
}


Page.prototype.completeForm = function(dialog_handler){
//	console.log('completeForm()!');
	if (! $$('.tt_form').length) 
		return ; 
	
	var _o = page_hash();
	if (_dialect == 'mysql' && _o['sctn'] == 'tbl' && _o['v'] == 'struct') {
		if (Object.keys(_o).contains('subv') && _o['subv'] != 'cols') {}
		else {
			updateSelectNeedsValues();					
		}

	}
	
	dialog_handler = dialog_handler || false;
	$$('.tt_form').each(function(form){
		// - function calls formResponseListener with needed variables
		// - hack to pass out the needed variables to an first class function
		var onFormResponse = function(text,xml) {
			formResponseListener(text,xml,form, page_hash(), dialog_handler);
		};
		
		// attach validation object
		var form_validator = new Form.Validator.Inline(form, {
			'evaluateFieldsOnBlur':false, 'evaluateFieldsOnChange': false
		});

		// add new vaildation
		// this validation is run only when the select element current value points 
		// to one of the predefined validation points
        form_validator.add('select_requires', {
            
			errorMsg: function(el){
				if (Object.keys(assets).contains('select_requires_err'))
					return assets['select_requires_err'];
				return 'there was an error';
            },
			
            test: function(el){
				var cls_itms = el.get('class').split(' ');
				var stmt = '';
				// loop through the classes and find that which satisfies the requirement
				// if the found class string has already being consumed (i.e. stored in assets)
				// then skip to the next class and set it has the one to be consumed (store in stmt)
				for (var _in = 0; _in < cls_itms.length; _in++) {
					var _temp = cls_itms[_in];
					if (! _temp.contains('select_requires:'))
						continue; // not a needed class item
		
					var _key = 'select_requires_stmt';
					if (Object.keys(assets).contains(_key) && assets[_key] == _temp)
						continue
					else {
						stmt = _temp;
						assets[_key] = stmt;
					}
					break; // the first class that satisfies this condition is the needed class
				}
				// description of each condition
				// select_requires:elmt_required:values
				var optns = stmt.split(':'); // ':' is the options delimiter
				var _vals = ( optns[2].contains('|') ) ? optns[2].split('|') : [ optns[2] ];
				// check if the value is one of the values and skips or ends the validation if its the last one
				if (!_vals.contains(el.value)) {
					return true; // assume to pass the test since it is not a needed value
				}
				// check if the elements specified in the second part of the description string
				// is set. if so it validates if not set error string
				if (! optns[1].contains('|') && $('id_'+ optns[1]).value )
					return true; // pass test
				else {
					assets['select_requires_err'] = 'This field requires '+ optns[1].split('_')[0] + ' field';
					return false; // fail test
				}
				
				return false; // failing is the default: for debugging sake
            }
        });

		// handle submission immediately after validation
		form_validator.addEvent('formValidate', function(status, form, e){
			e.stop(); // stop propagation of event and also prevent default
			if (!status) return; // form didn't validate
			// submit the values of the form
			new XHR({
				url: generate_ajax_url(),
				spinnerTarget: form,
				onSuccess: onFormResponse
			}).post(form.toQueryString());

		});		
	});
}


var XHR = new Class({

	Extends: Request,
	
	initialize: function(options) {
		options.headers = {
			'X-CSRFToken': Cookie.read('csrftoken')
		};
		options.chain = 'link';
		
		// append ajax validation key
		options.url += '&ajaxKey=' + _ajaxKey;
		this.parent(options);
		
		if (options && options.showLoader != false) {
			
			this.addEvent('onRequest', function() {
				var spinnerTarget = (options.spinnerTarget) ? options.spinnerTarget: document.body;
				var ajaxSpinner = new Spinner(spinnerTarget, {'message': 'loading data...'});
				show('header-load');
				ajaxSpinner.show(true);
				
				this.addEvent('onComplete', function(xhr){
					hide('header-load');
					ajaxSpinner.hide();
					ajaxSpinner.destroy();
				});				
			});

		}
		
		this.addEvent("onSuccess", function() {});
		
		// redirect page based on Cookie
		this.addEvent('onComplete', function() {
			if (Cookie.read('TT_SESSION_TIMEOUT')) {
				Cookie.dispose('TT_SESSION_TIMEOUT');
				Cookie.write('TT_NEXT', Object.toQueryString(page_hash()));
			    // funny redirect
		        location.href = location.protocol + '//'+ location.host + location.pathname + 'login/';
			}
		});
		
		var msg = 'An unexpected error was encountered. Please reload the page and try again.';
		this.addEvent("onException", function() {
			showDialog("Exception", msg, {'draggable':false,'overlayClick':false});
		});
		
		this.addEvent("onFailure", function(xhr) {
			if (xhr.status == 500 && xhr.statusText == "UNKNOWN STATUS CODE") msg = xhr.response;
//				hide('header-load');
//                ajaxSpinner.hide();
			if (msg == 'invalid ajax request!') 
				location.reload()
			else
				showDialog('Error!', msg, {'draggable':false,'overlayClick':false})
		});
	},
	
	// redefined to avoid auto script execution
	success: function(text, xml) {
		this.onSuccess(text, xml);
	}
	
});


function updateSelectNeedsValues(){
//	console.log('updateSelectNeedsValues');
	var selects = $$('.tt_form .compact-form select');
	for (var _in = 0; _in < selects.length; _in++) {
		var sel_item = selects[_in];
		if (! sel_item.get('class').contains('needs:'))
			continue;
		
		// find definition statement
		var stmt = '';
		sel_item.get('class').split(' ').each(function(class_item){
			if (class_item.contains('needs') )
				stmt = class_item;
		});
		//
		var stmt_cond = stmt.split(':');
		sel_item.addEvent('change', function(e){
			if (stmt_cond[2].split('|').contains(e.target.value))
				e.target.getParent('table').getElements('.'+stmt_cond[1]+'-needed').removeClass('hidden');
			else
				e.target.getParent('table').getElements('.'+stmt_cond[1]+'-needed').addClass('hidden');
		});
		
	}

}

