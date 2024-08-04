local M = {}

M.showSongs = function (songs)
  local pickers = require "telescope.pickers"
  local finders = require "telescope.finders"
  local sorters = require "telescope.sorters"
  local actions = require('telescope.actions')

  pickers.new({}, {
    prompt_title = "Tracks",
    finder = finders.new_table(songs),
    sorter = sorters.get_generic_fuzzy_sorter({}),
    attach_mappings = function(prompt_bufnr, map)
      actions.select_default:replace(function()
        actions.close(prompt_bufnr)
        local selection = require('telescope.actions.state').get_selected_entry()
        print("You selected: " .. selection.value)
      end)
      return true
    end,
  }):find()
end

M.showPlaylists = function (playlists)
  local pickers = require "telescope.pickers"
  local finders = require "telescope.finders"
  local sorters = require "telescope.sorters"
  local actions = require('telescope.actions')

  vim.print(playlists)

  pickers.new({}, {
    prompt_title = "Spotify Playlists",
    finder = finders.new_table {
      results = playlists,
      entry_maker = function(entry)
        return {
          value = entry,
          display = entry.name,
          ordinal = entry.name,
        }
      end,
    },
    sorter = sorters.get_generic_fuzzy_sorter({}),
    attach_mappings = function(prompt_bufnr, map)
      actions.select_default:replace(function()
        actions.close(prompt_bufnr)
        local selection = require('telescope.actions.state').get_selected_entry()
        vim.api.nvim_command("SpotifyPlay " .. selection.value.uri)
        print("You selected: " .. selection.value.id)
      end)
      return true
    end,
  }):find()
end

return M
