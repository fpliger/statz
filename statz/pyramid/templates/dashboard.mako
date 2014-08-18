# -*- coding: utf-8 -*- 
<%inherit file="layout.mako"/>

<h1>Task's List</h1>

<ul id="tasks">
% if routes.values():
  % for url, route in routes.items():
  <li>
    <span class="name">${route.get('url', url.replace('_', '/'))}</span>
    <span class="actions">
      [ <a href="#">close</a> ]
    </span>
  </li>
  % endfor
% else:
  <li>There are no routes?!</li>
% endif
</ul>