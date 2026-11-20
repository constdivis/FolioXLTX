local function has_class(classes, wanted)
  for _, class in ipairs(classes) do
    if class == wanted then
      return true
    end
  end
  return false
end

local function remove_class(classes, unwanted)
  local result = {}
  for _, class in ipairs(classes) do
    if class ~= unwanted then
      table.insert(result, class)
    end
  end
  return result
end

function Span(element)
  if has_class(element.classes, "mark") then
    element.classes = remove_class(element.classes, "mark")
    element.attributes["custom-style"] = "DraftInline"
    return element
  end
end

function Div(element)
  if has_class(element.classes, "draft") then
    element.classes = remove_class(element.classes, "draft")
    element.attributes["custom-style"] = "Draft"
    return element
  end
end
