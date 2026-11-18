function(luxvelum_build_id out)
    if(DEFINED ENV{GITHUB_SHA} AND DEFINED ENV{GITHUB_REF_NAME})
        string(SUBSTRING "$ENV{GITHUB_SHA}" 0 7 commit)
        set(${out} "$ENV{GITHUB_REF_NAME} ${commit}" PARENT_SCOPE)
        return()
    endif()
    find_package(Git QUIET)
    if(GIT_FOUND)
        execute_process(COMMAND "${GIT_EXECUTABLE}" rev-parse --short=7 HEAD
                        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" OUTPUT_VARIABLE commit
                        OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
        execute_process(COMMAND "${GIT_EXECUTABLE}" rev-parse --abbrev-ref HEAD
                        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" OUTPUT_VARIABLE branch
                        OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
    endif()
    if(commit)
        set(${out} "${branch} ${commit} local" PARENT_SCOPE)
    else()
        set(${out} "local" PARENT_SCOPE)
    endif()
endfunction()
