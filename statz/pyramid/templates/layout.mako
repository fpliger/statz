# -*- coding: utf-8 -*-

<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="">
    <meta name="author" content="">
##    <link rel="icon" href="/statz/static/img/favicon.ico">

    <title>Statz Dashboard</title>

    <!-- Bootstrap core CSS -->
    <link href="/statz/static/css/bootstrap.min.css" rel="stylesheet">

    <!-- Custom styles for this template -->
    <link href="/statz/static/css/dashboard.css" rel="stylesheet">

    <!-- HTML5 shim and Respond.js IE8 support of HTML5 elements and media queries -->
    <!--[if lt IE 9]>
      <script src="https://oss.maxcdn.com/html5shiv/3.7.2/html5shiv.min.js"></script>
      <script src="https://oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>
    <![endif]-->
  </head>

  <body>

    <div id="top_menu_bar" class="navbar navbar-inverse navbar-fixed-top" role="navigation">
      <div class="container-fluid">
        <div class="navbar-header">
          <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-collapse">
            <span class="sr-only">Toggle navigation</span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
          </button>
          <a class="navbar-brand" href="#">Statz</a>
        </div>
        <div class="navbar-collapse collapse">
          <ul class="nav navbar-nav navbar-right">
            <li><a href="#">Dashboard</a></li>
            <li><a href="#">Settings</a></li>
            <li><a href="#">Profile</a></li>
            <li><a href="#">Help</a></li>
          </ul>
          <form class="navbar-form navbar-right">
            <input type="text" class="form-control" placeholder="Search...">
          </form>
        </div>
      </div>
    </div>

    <div class="container-fluid main">
      <div class="row">
        <div class="col-md-2">
          <ul class="nav nav-sidebar affix">
            <li class="active"><a href="#">Calls</a></li>
              <ul class="nav">
                  % for url, route in routes.items():
                    <li><a href="#${url}">${route.get('url', url.replace('_', '/'))}</a></li>
                  % endfor
              </ul>
          </ul>
        </div>
        <div class="col-lg-10 col-md-0">
            <div class="panel panel-default">
                <div class="panel-body">
                  <h1 class="page-header">Dashboard</h1>

                  <div class="table-responsive">
                    %for url, route in routes.items():
                        <h1 id="${url}" class="page-header view-section">${route.get('url', url.replace('_', '/'))}

                        <span>

                        <div class="btn-group">

                           %for methname in route.get('methods', []):
                            <a type="button" class="btn btn-default" href="#${url}_${methname}">${methname}</a>
                           %endfor

                            %if route.get('calls', []):
                            <button type="button" class="btn btn-default" onclick="$('#table_${url}').toggle();">Show/Hide</button>


                          <div class="btn-group">
                            <button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown">
                              Dropdown
                              <span class="caret"></span>
                            </button>
                            <ul class="dropdown-menu" role="menu">
                                %for k in route:
                                    <li><a href="#">${k}</a></li>
                                %endfor
                            </ul>
                          </div>

                            %endif
                        </div>
                        </span>

                    </h1>

                    %for methname, info in route.get('methods', {}).items():
                    <div id="${url}_${methname}" class="bs-docs-section method-section">
                        <h4>${methname} ${route.get('url', url.replace('_', '/'))}
                            %if info.get('calls', []):
                             <span class="badge" style="margin-left: 20px;">${info['calls'][-1]['response_type']}</span>
                            %endif

                            <span style="margin-left: 20px;">

                    <div class="btn-group">

                        % if info.get('code', ''):
                        <button type="button" class="btn btn-default" onclick="$('#${url}_${methname}_code').toggle();">Code</button>
                        % endif
                        %if info.get('calls', []):
                        <button type="button" class="btn btn-default" onclick="$('#table_${url}_${methname}_params').toggle();">Parameters</button>
                        <button type="button" class="btn btn-default" onclick="$('#table_${url}_${methname}_headers').toggle();">Headers</button>
                        <button type="button" class="btn btn-default" onclick="$('#table_${url}_${methname}_resp_obj').toggle();">Response Object</button>
                        <button type="button" class="btn btn-default" onclick="$('#table_${url}_${methname}').toggle();">Calls</button>
                        % endif
                    </div>
                    </span>
                        </h4>

                        <div id="${url}_${methname}_docstring">
                            ${info.get('docstring', '---') | n}
                        </div>


                        <div id="${url}_${methname}_code" style="display:none;">
                            <h4>Related View Code:</h4>
                            ${info.get('code', '---') | n}
                        </div>

                         %if info.get('calls', []):

                             <div id="table_${url}_${methname}_params"  style="display:none;">
                                <h4>Parameters:</h4>

                                 ${render_key_value_table("inner_table_" + url + "_" + methname + "_params", info['calls'][-1]['request_params'], style="") | n}
                             </div>

                             <div id="table_${url}_${methname}_headers"  style="display:none;">
                                <h4>Headers:</h4>
                                ${render_key_value_table("inner_table_" + url + "_" + methname + "_headers", info['calls'][-1]['headers'], style="") | n}
                             </div>

                             <div id="table_${url}_${methname}_resp_obj"  style="display:none;">
                                <h4>Response Object:</h4>
                                ${render_key_value_table("inner_table_" + url + "_" + methname + "_resp_obj", info['calls'][-1]['response_json_body'], style="") | n}
                             </div>

                             <div id="table_${url}_${methname}"  style="display:none;">
                                <h4>Most Recent Calls:</h4>

                                <table id="inner_table_${url}_${methname}" class="table table-striped">
                                  <thead>

                                    <tr>
                                      <th>#</th>
                                        %for col in ['session', 'timestamp', 'duration', 'response_status', 'response_type', 'memory']:
                                            <th>${col}</th>
                                        %endfor
                                    </tr>
                                  </thead>
                                  <tbody>
                                    % for ind, call in enumerate(info.get('calls', [])):
                                    <tr>
                                      <td>${ind}</td>
                                       % for col in ['session', 'timestamp', 'duration', 'response_status', 'response_type', 'memory']:
                                      <td>${fmt(col, call.get(col, '???'))}</td>
                                       % endfor
                                    </tr>
                                    %endfor
                                  </tbody>
                                </table>
                              </div>
                       %endif

                    </div>

                    %endfor


                      %endfor
                  </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bootstrap core JavaScript
    ================================================== -->
    <!-- Placed at the end of the document so the pages load faster -->
    <script src="/statz/static/js/jquery-1.10.2.min.js"></script>
    <script src="/statz/static/js/bootstrap.min.js"></script>
  </body>
</html>
