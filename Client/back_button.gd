extends Button

const MARGIN_PX := 12.0
const WIDTH_PX := 88.0
const HEIGHT_PX := 44.0
const FONT_PX := 17.0

func _ready() -> void:
	pressed.connect(_go_back)
	get_tree().root.size_changed.connect(_place)
	_place.call_deferred()


func _go_back() -> void:
	if not OS.has_feature("web"):
		return
	JavaScriptBridge.eval("""
		var win = (window.parent && window.parent !== window) ? window.parent : window;
		if (win.history.length > 1) {
			win.history.back();
		} else {
			win.location.href = '/feishu-games/';
		}
	""")


func _place() -> void:
	var view := get_viewport().get_visible_rect().size
	var win := Vector2(DisplayServer.window_get_size())
	if view.x <= 1.0 or win.x <= 1.0:
		return
	var to_game := view.x / win.x
	var safe := _safe_insets()
	var left := (safe.x + MARGIN_PX) * to_game
	var top := (safe.y + MARGIN_PX) * to_game
	var width := WIDTH_PX * to_game
	var height := HEIGHT_PX * to_game
	offset_left = left
	offset_top = top
	offset_right = left + width
	offset_bottom = top + height
	add_theme_font_size_override("font_size", maxi(int(round(FONT_PX * to_game)), 16))


func _safe_insets() -> Vector2:
	if not OS.has_feature("web"):
		return Vector2.ZERO
	var raw = JavaScriptBridge.eval("""
		(function () {
			var probe = document.createElement('div');
			probe.style.cssText = 'position:fixed;visibility:hidden;padding-top:env(safe-area-inset-top);padding-left:env(safe-area-inset-left);';
			document.body.appendChild(probe);
			var cs = getComputedStyle(probe);
			var top = parseFloat(cs.paddingTop) || 0;
			var left = parseFloat(cs.paddingLeft) || 0;
			probe.remove();
			var vv = window.visualViewport;
			if (vv && vv.offsetTop > top) {
				top = vv.offsetTop;
			}
			return top + ',' + left;
		})()
	""")
	if typeof(raw) != TYPE_STRING:
		return Vector2.ZERO
	var parts: PackedStringArray = raw.split(",")
	if parts.size() != 2 or not parts[0].is_valid_float() or not parts[1].is_valid_float():
		return Vector2.ZERO
	return Vector2(parts[1].to_float(), parts[0].to_float())
