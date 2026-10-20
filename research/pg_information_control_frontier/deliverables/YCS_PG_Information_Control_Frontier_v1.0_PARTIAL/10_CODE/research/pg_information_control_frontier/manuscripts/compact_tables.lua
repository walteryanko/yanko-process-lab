function Table(t)
  if FORMAT:match('latex') then
    return {pandoc.RawBlock('latex', '\\begingroup\\footnotesize'), t, pandoc.RawBlock('latex', '\\endgroup')}
  end
end
