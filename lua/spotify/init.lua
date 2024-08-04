local M = {}

M.showTracks = function (songs)
  local pickers = require "telescope.pickers"
  local finders = require "telescope.finders"
  local sorters = require "telescope.sorters"
  local actions = require('telescope.actions')

  pickers.new({}, {
    prompt_title = "Tracks",
    finder = finders.new_table {
      results = songs,
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
        vim.print("Playing " .. selection.value.uri)
        vim.api.nvim_command("SpotifyPlay " .. selection.value.uri)
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
        vim.print("Playing " .. selection.value.uri)
      end)
      map('i', '<C-d>', function()
        actions.close(prompt_bufnr)
        local selection = require('telescope.actions.state').get_selected_entry()
        local tracks = M.getPlaylistTracks(selection.value.id)
        M.showTracks(tracks)
      end)
      return true
    end,
  }):find()
end

M.getPlaylistTracks = function (playlistId)
  local p = vim.api.nvim_call_function("SpotifyGetPlaylistTracks", { playlistId })
  return p
end

return M
